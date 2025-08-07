
# Instructor Metrics & Feedback CLI

## Overview
This CLI helps instructors query student progress and analyze feedback from course data stored in a SQLite database.  
It supports **two main features**:

1. **Part A – Metrics Queries**  
   - Answer natural-language questions about enrollments, completions, scores, and time spent.
   - Uses a *hybrid approach*: a rule-based intent parser maps questions to a set of **safe, parameterized SQL templates** in `metrics.json`.
   - Outputs a **single numeric answer** with context for auditing.

2. **Part B – Feedback Analysis**  
   - Summarizes **quantitative** (ratings) and **qualitative** (comments) feedback from students.
   - Works at **module level** and **course level**.
   - Aggregates ratings and returns all raw comments for instructor review.

---

## Approach

### Part A – Metrics
- **Data ingestion**: All provided CSV/TSV files are loaded into a SQLite database (`user.db`) with tables mirroring file names (`students`, `modules`, `assessments`, `student_module_completions`, `student_assessment_completions`).
- **Metrics registry**:  
  - `metrics.json` contains canonical metric definitions (name, required parameters, SQL).
  - All SQL templates are reviewed, parameterized, and safe from injection.
- **Natural Language → Metric Mapping**:  
  - A small, rule-based parser (`intent_parser.py`) detects the metric and extracts IDs from the question.
  - The parser only maps to known metrics—no free-form SQL generation.
- **Execution**:  
  - The CLI loads the SQL from the registry, fills in parameters, executes against `user.db`, and prints the numeric result.

This approach ensures **safety, reproducibility, and auditability** while supporting the most common instructor questions.

---

### Part B – Feedback
- **Quantitative**:  
  - Aggregates student ratings per module:
    - Number of ratings
    - Average rating
    - Count of each rating level (1–5)
- **Qualitative**:  
  - Collects all non-empty `feedback` comments from `student_module_completions`.
  - Displays comments as-is for instructor review (no LLM summarization).
- **Course-level aggregation**:
  - Iterates over all modules in the course and compiles the above analysis for each.

This design gives instructors:
- A quick **numerical snapshot** of satisfaction.
- The **exact words** students used to express their experiences.
- The ability to see trends both **module-by-module** and across the whole course.

---

## Usage

### Part A – Metrics
```bash
# Ask a question
python3 cli.py ask "How many students are enrolled?"
python3 cli.py ask "How many students have completed module 2?"
python3 cli.py ask "How many students have completed assessment 2 but not assessment 4?"
python3 cli.py ask "What was the average score on assessment 3?"
python3 cli.py ask "What is student 7's average score?"
python3 cli.py ask "How long did students spend on module 1?"
python3 cli.py ask "What was the average rating for module 5?"
python3 cli.py ask "How many students have completed the course?"
```

---

### Part B – Feedback
```bash
# Module-level feedback (ratings + comments)
python3 cli.py feedback-module 2

# Course-level feedback (all modules)
python3 cli.py feedback-course
```

---

## Extending the System
- **New metrics**: Add to `metrics.json` (SQL + params), then extend `intent_parser.py` to recognize new questions.
- **More parsing flexibility**: Add name-to-ID resolution for modules/assessments.
- **Filters**: Extend SQL templates to allow filtering by date, min score, or other criteria.
