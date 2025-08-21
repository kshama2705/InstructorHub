# InstructorHub — Metrics & Feedback CLI

A CLI “talk to your course” experience for Uplimit instructors. It supports:

- **Part A – Metrics Q&A**: ask questions like “How many students completed module Foundations of Education?”  
  We use a **LLaMA-based NL intent parser** to map the question to a **known metric** and **parameters**, then execute a **parameterized SQL template** from `metrics.json` against `user.db`. If the LLM can’t parse or lacks context, we **fall back to a rules-based parser**.
- **Part B – Feedback**: view **quantitative** rating aggregates and **qualitative** comments for each module, and across the course.

This repo is designed to be **reliable, correct, and auditable**. The LLM **never writes SQL**. It only chooses `(metric, params)` which are validated against a **metric registry** before execution.

---

## Why this approach (reliability & correctness)

- **Semantic metric registry (`metrics.json`)**: Every supported question resolves to a **canonical metric** backed by a **reviewed, parameterized SQL** template (no free-form text2sql). This makes the system predictable and auditable. 
- **LLaMA intent parser (default)**: LLaMA converts natural language into `{ "metric": <name>, "params": {...} }`. We then **validate** the metric name against the registry and **coerce**/resolve the parameters, including **name→ID mapping** using the DB (e.g., “Final Exam” → `assessment_id`).
- **Rules-based fallback**: If the LLM returns invalid JSON, unknown metrics, or unmappable params, we fall back to a small **rules parser** so the CLI remains functional without an API.
- **Parameterization only**: Queries run through **parameterized SQL** with a read-only DB connection; no DDL/DML; short timeouts recommended. This keeps correctness and security high.
- **Simple, testable surface**: For each metric, unit tests can validate both the SQL and the parsing (LLM & rules) with paraphrases.

The initial registry includes counts, averages, set-differences, and time aggregations covering the example questions from the brief. See `metrics.json`. 

---

## Project structure

```
cli.py                  # CLI entry point (LLM-first; rules fallback). Commands: ask / feedback-module / feedback-course
llama_client.py         # (optional) OpenAI-compatible client for LLaMA endpoints
llama_intent_parser.py  # LLaMA-first parser: builds context, calls API, validates & coerces params, name→ID mapping
intent_parser.py        # Rules-based fallback parser (IDs in the question)
metric_registry.py      # Loads & validates metrics.json; renders SQL + param dict
metrics.json            # Canonical metrics with required params and parameterized SQL templates
executor.py             # Executes a single-aggregate SQL and returns the numeric value
db.py                   # DB connection helper (use query-only/timeout pragmas in production)
feedback.py             # Part B: rating aggregates + qualitative comments (module & course level)
user.db                 # SQLite database built from the provided course CSV/TSV files
requirements.txt        # Python dependencies
.env.example            # Template for API keys & endpoint config
README.md               # This file
```

The previous version of the README is preserved in spirit but expanded here with LLM details. fileciteturn2file1

---

## Setup

This guide explains how to set up your environment for running the **InstructorHub** CLI application using **conda** and environment variables.

---

## 1. Clone or Extract the Project

If you received the project as a `.zip` file:

```bash
unzip InstructorHub_package.zip -d InstructorHub
cd InstructorHub
```

If you received it from GitHub (private repo):

```bash
git clone <repo-url>
cd InstructorHub
```

---

## 2. Create and Activate a Conda Environment

We recommend Python 3.10+.

```bash
conda create -n instructorhub python=3.10 -y
conda activate instructorhub
```

---

## 3. Install Dependencies

Make sure you are inside the `InstructorHub` folder (where `requirements.txt` is located).

```bash
pip install -r requirements.txt
```

---

## 4. Environment Variables

This project uses **environment variables** to configure LLaMA API access (and optionally other APIs).

We use a `.env` file to store these.

### 4.1 Copy the Example `.env`

```bash
cp .env.example .env
```

### 4.2 Edit `.env`

Open `.env` in your text editor and fill in:

```env
LLAMA_API_KEY=your_llama_api_key_here
LLAMA_API_BASE=https://api.llama-api.meta.com/v1
```

Replace `your_llama_api_key_here` with your **Meta LLaMA API key** from [LLaMA Developer Portal](https://llama.developer.meta.com/).

> **Note**: `LLAMA_API_BASE` may differ depending on your account configuration.

---

## 5. Running the CLI

Once the environment is set up, you can run queries.

### 5.1 Using the LLaMA Parser (Default)

```bash
python cli.py ask "How many students completed module Foundations of Education?"
```

### 5.2 Using the Rule-Based Parser Only

If you don’t have LLaMA API credentials, bypass LLaMA parsing:

```bash
python cli.py ask "How many students completed module 1?" --rules-only
```

---

## 6. Feedback Insights

For Part B (feedback analysis):

```bash
# Module-level feedback (requires module ID)
python cli.py feedback-module 1

# Course-level feedback (all modules)
python cli.py feedback-course
```

---

You’re now ready to run InstructorHub!


---

## Usage

### Part A — Metrics Q&A
Ask any supported question in natural language:

```bash
python3 cli.py ask "How many students are enrolled?"
python3 cli.py ask "How many students completed module Foundations of Education?"
python3 cli.py ask "What was the average score on the Final Exam?"
python3 cli.py ask "What is student 7's average score?"
python3 cli.py ask "How long did students spend on module Technology in Education?"
python3 cli.py ask "What was the average rating for module 5?"
python3 cli.py ask "How many students have completed the course?"
```

- **Output**: a single numeric answer to stdout, and a small audit trailer (metric + params) to stderr.
- **Rules-only mode** (skip LLaMA):
```bash
python3 cli.py --rules-only ask "How many students have completed module 2?"
```

### Part B — Feedback with LLM summarization
In addition to showing aggregated quantitative ratings and full qualitative comments, Part B uses the LLaMA API to automatically generate a structured summary of feedback.

For each module (or for the course as a whole), the CLI will now return:

Summary – a one-paragraph sentiment overview

Themes – key discussion topics

Praise – positive aspects students highlighted

Issues – common challenges or complaints

Suggestions – actionable improvements

This gives instructors both raw transparency (full comments) and actionable insights without manually reading every comment.
```bash
# Module-level (ratings + comments)
python3 cli.py feedback-module 2

# Course-level (aggregated per module)
python3 cli.py feedback-course
```

---

## Extensibility

- **Add metrics**: update `metrics.json` with a new `name`, `params`, and `sql` template; then teach the parsers to recognize the phrasing (rules and/or LLaMA few-shots).
- **Richer filters**: add date ranges (e.g., `start_date`, `end_date`), thresholds (`min_score`), or cohorts; expose them as params in the metric and update parsers.
- **Better names**: augment the name→ID resolver to support more synonyms or fuzzy matches.
- **Qualitative insights**: optionally add an LLM-based summarizer for comments (prompted to extract themes + suggestions). Keep it off by default to avoid cost/noise unless needed.



## Metrics registry (examples)

We ship templates for the questions listed in the brief (counts, averages, time). See `metrics.json` for the full list and SQL. fileciteturn2file0
