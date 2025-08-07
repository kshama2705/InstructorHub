# feedback.py
import sqlite3
from typing import List, Dict, Any
from db import get_conn

# --- Quantitative aggregation ---
def aggregate_module_feedback(db_path: str, module_id: int) -> Dict[str, Any]:
    """
    Returns aggregated quantitative feedback for a module:
    - count of responses
    - average rating
    - rating distribution
    """
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "SELECT COUNT(rating) AS count, AVG(rating) AS avg,"
            " SUM(CASE WHEN rating=1 THEN 1 ELSE 0 END) AS r1,"
            " SUM(CASE WHEN rating=2 THEN 1 ELSE 0 END) AS r2,"
            " SUM(CASE WHEN rating=3 THEN 1 ELSE 0 END) AS r3,"
            " SUM(CASE WHEN rating=4 THEN 1 ELSE 0 END) AS r4,"
            " SUM(CASE WHEN rating=5 THEN 1 ELSE 0 END) AS r5"
            " FROM student_module_completions"
            " WHERE module_id = ? AND rating IS NOT NULL;",
            (module_id,)
        )
        row = cur.fetchone()
        keys = ['count','average','r1','r2','r3','r4','r5']
        return dict(zip(keys, row))

# --- Qualitative collection ---
def get_module_comments(db_path: str, module_id: int) -> List[str]:
    with get_conn(db_path) as conn:
        cur = conn.execute(
            "SELECT feedback FROM student_module_completions"
            " WHERE module_id = ? AND feedback IS NOT NULL;",
            (module_id,)
        )
        return [r[0] for r in cur.fetchall()]

# --- Higher-level wrappers ---
def module_feedback(db_path: str, module_id: int) -> Dict[str, Any]:
    """
    Combines quantitative and qualitative analysis for a module.
    """
    quant = aggregate_module_feedback(db_path, module_id)
    comments = get_module_comments(db_path, module_id)
    return {"quantitative": quant, "comments": comments}


def course_feedback(db_path: str) -> Dict[int, Any]:
    """
    Returns feedback for all modules as a dict of module_id -> analysis.
    """
    with get_conn(db_path) as conn:
        cur = conn.execute("SELECT DISTINCT module_id FROM student_module_completions;")
        mids = [r[0] for r in cur.fetchall()]
    result = {}
    for mid in mids:
        result[mid] = module_feedback(db_path, mid)
    return result


