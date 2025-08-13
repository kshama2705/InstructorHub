# feedback.py
from typing import List, Dict, Any, Optional
from db import get_conn

# Try to import the LLaMA client (OpenAI-compatible) if present
try:
    from llama_client import chat_llama, LlamaClientError  # your existing client
    _LLM_OK = True
except Exception:
    chat_llama = None
    LlamaClientError = Exception
    _LLM_OK = False


# ---------- Quantitative aggregation ----------
def aggregate_module_feedback(db_path: str, module_id: int) -> Dict[str, Any]:
    """
    Aggregated quantitative feedback for a module:
    - count of ratings
    - average rating
    - rating distribution (1..5)
    """
    with get_conn(db_path) as conn:
        cur = conn.execute(
            """
            SELECT
              COUNT(rating) AS count,
              AVG(rating)  AS average,
              SUM(CASE WHEN rating = 1 THEN 1 ELSE 0 END) AS r1,
              SUM(CASE WHEN rating = 2 THEN 1 ELSE 0 END) AS r2,
              SUM(CASE WHEN rating = 3 THEN 1 ELSE 0 END) AS r3,
              SUM(CASE WHEN rating = 4 THEN 1 ELSE 0 END) AS r4,
              SUM(CASE WHEN rating = 5 THEN 1 ELSE 0 END) AS r5
            FROM student_module_completions
            WHERE module_id = ? AND rating IS NOT NULL;
            """,
            (module_id,),
        )
        row = cur.fetchone()

        keys = ["count", "average", "r1", "r2", "r3", "r4", "r5"]
        return dict(zip(keys, row))


def get_module_comments(db_path: str, module_id: int) -> List[str]:
    with get_conn(db_path) as conn:
        cur = conn.execute(
            """
            SELECT feedback
            FROM student_module_completions
            WHERE module_id = ? AND feedback IS NOT NULL AND TRIM(feedback) <> '';
            """,
            (module_id,),
        )
        return [r[0] for r in cur.fetchall()]


def _get_module_name(db_path: str, module_id: int) -> Optional[str]:
    with get_conn(db_path) as conn:
        cur = conn.execute("SELECT module_name FROM modules WHERE module_id = ?;", (module_id,))
        row = cur.fetchone()
        return row[0] if row else None


# ---------- LLM summarization ----------
def _summarize_comments_with_llm(comments: List[str], module_name: Optional[str], quant: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Returns a dict like:
      {
        "summary": "...short paragraph...",
        "themes": ["...", "..."],
        "praise": ["...", "..."],
        "issues": ["...", "..."],
        "suggestions": ["...", "..."]
      }
    or None if LLM unavailable or no comments.
    """
    if not _LLM_OK or not comments:
        return None

    # Light trimming to stay within token limits
    MAX_COMMENTS = 200
    MAX_CHARS_PER = 500
    trimmed = [c.strip()[:MAX_CHARS_PER] for c in comments[:MAX_COMMENTS]]

    module_label = module_name or "This module"
    avg = quant.get("average")
    try:
        avg_disp = f"{float(avg):.2f}" if avg is not None else "N/A"
    except Exception:
        avg_disp = "N/A"
    quant_bits = (
        f"Ratings: count={quant.get('count', 0)}, avg={avg_disp}, "
        f"distribution={{1:{quant.get('r1',0)},2:{quant.get('r2',0)},3:{quant.get('r3',0)},4:{quant.get('r4',0)},5:{quant.get('r5',0)}}}"
    )

    system = (
        "You analyze student feedback for a course module and return useful, concise, and actionable insights "
        "as STRICT JSON with keys: summary (string), themes (array), praise (array), issues (array), suggestions (array). "
        "Be specific, avoid fluff, avoid repeating comments verbatim, and give concrete suggestions."
    )
    user = (
        f"Module: {module_label}\n"
        f"{quant_bits}\n\n"
        "Here are student comments (one per line):\n"
        + "\n".join(f"- {c}" for c in trimmed)
        + "\n\nReturn STRICT JSON ONLY with keys: summary, themes, praise, issues, suggestions."
    )

    try:
        content = chat_llama(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
        )
    except LlamaClientError:
        return None
    except Exception:
        return None

    # ---- Robust JSON extraction ----
    raw = content.strip()

    # 1) Strip common markdown fences: ```json ... ``` or ``` ... ```
    def strip_fences(s: str) -> str:
        s = s.strip()
        if s.startswith("```"):
            s = s.lstrip("`")
            # remove leading "json" or language tag if present
            if s.lower().startswith("json"):
                s = s[4:].lstrip("\n ").lstrip()
            # content after the opening fence until another fence or end
            # we'll just strip trailing backticks too
            s = s.rstrip("`").strip()
        # Also handle leading "json\n{...}"
        if s.lower().startswith("json\n"):
            s = s[5:].lstrip()
        return s

    cleaned = strip_fences(raw)

    # 2) If still not pure JSON, try to locate the first {...} block
    import json, re
    def find_json_block(s: str) -> Optional[str]:
        # naive brace matching to get the first JSON object
        start = s.find("{")
        if start == -1:
            return None
        depth = 0
        for i, ch in enumerate(s[start:], start=start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return s[start:i+1]
        return None

    try_texts = [cleaned, find_json_block(cleaned) or raw]
    data = None
    for t in try_texts:
        if not t:
            continue
        try:
            data = json.loads(t)
            break
        except Exception:
            continue

    if data is None:
        # Fall back: return the raw text as summary
        return {"summary": raw, "themes": [], "praise": [], "issues": [], "suggestions": []}

    # 3) Normalize fields (accept strings or lists)
    def as_list(x):
        if x is None:
            return []
        if isinstance(x, list):
            return x
        if isinstance(x, str):
            # split on newline or semicolons if a single string was returned
            parts = [p.strip("- •\t ").strip() for p in re.split(r"[;\n]", x) if p.strip()]
            return parts
        return [str(x)]

    out = {
        "summary": data.get("summary") or "",
        "themes": as_list(data.get("themes")),
        "praise": as_list(data.get("praise")),
        "issues": as_list(data.get("issues")),
        "suggestions": as_list(data.get("suggestions")),
    }
    return out


# ---------- High-level wrappers ----------
def module_feedback(db_path: str, module_id: int) -> Dict[str, Any]:
    """
    Combines quantitative + qualitative + (optional) LLM summary for one module.
    Always returns 'quantitative' and 'comments'. If LLM is available, also
    returns 'insights' with summary/themes/praise/issues/suggestions.
    """
    quant = aggregate_module_feedback(db_path, module_id)
    comments = get_module_comments(db_path, module_id)
    module_name = _get_module_name(db_path, module_id)

    out = {
        "module_id": module_id,
        "module_name": module_name,
        "quantitative": quant,
        "comments": comments,           # raw, unfiltered
    }

    insights = _summarize_comments_with_llm(comments, module_name, quant)
    if insights:
        out["insights"] = insights

    return out


def course_feedback(db_path: str) -> Dict[int, Any]:
    """
    Returns analysis for all modules: {module_id: module_feedback(...)}
    """
    with get_conn(db_path) as conn:
        cur = conn.execute("SELECT DISTINCT module_id FROM student_module_completions;")
        module_ids = [r[0] for r in cur.fetchall()]

    result: Dict[int, Any] = {}
    for mid in module_ids:
        result[mid] = module_feedback(db_path, mid)
    return result
