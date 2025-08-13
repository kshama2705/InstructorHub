import os
import json
import re
import sys
from typing import Optional, Dict, Any
from db import get_conn
from intent_parser import parse_question as rules_parse

# Try to import LLM client, fall back gracefully if not available
try:
    from llama_client import chat_llama, LlamaClientError
    LLAMA_AVAILABLE = True
except ImportError:
    LLAMA_AVAILABLE = False
    LlamaClientError = Exception


def get_database_schema(db_path: str) -> str:
    """Get database schema information for the LLM context."""
    with get_conn(db_path) as conn:
        # Get table names and their schemas
        tables_info = []
        
        # Get all table names
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]
        
        for table in tables:
            # Get column info for each table
            cursor = conn.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            
            col_info = []
            for col in columns:
                col_name, col_type = col[1], col[2]
                col_info.append(f"{col_name} ({col_type})")
            
            tables_info.append(f"- {table}: {', '.join(col_info)}")
        
        return "\n".join(tables_info)


def get_available_metrics(registry) -> str:
    """Get available metrics from the registry for LLM context."""
    metrics = registry.names()
    metric_descriptions = []
    
    for metric in metrics:
        spec = registry.get(metric)
        params = spec.get("params", [])
        param_str = f" (requires: {', '.join(params)})" if params else ""
        metric_descriptions.append(f"- {metric}{param_str}")
    
    return "\n".join(metric_descriptions)


def extract_module_id_by_name(db_path: str, module_name: str) -> Optional[int]:
    """Try to find module ID by name from the database."""
    with get_conn(db_path) as conn:
        cursor = conn.execute(
            "SELECT module_id FROM modules WHERE LOWER(module_name) LIKE LOWER(?)",
            (f"%{module_name}%",)
        )
        result = cursor.fetchone()
        return result[0] if result else None


def extract_assessment_id_by_name(db_path: str, assessment_name: str) -> Optional[int]:
    """Try to find assessment ID by name from the database."""
    with get_conn(db_path) as conn:
        cursor = conn.execute(
            "SELECT assessment_id FROM assessments WHERE LOWER(assessment_name) LIKE LOWER(?)",
            (f"%{assessment_name}%",)
        )
        result = cursor.fetchone()
        return result[0] if result else None


def llama_parse_question(question: str, registry, db_path: str) -> Optional[Dict[str, Any]]:
    """Use LLM to parse natural language question into metric intent."""
    if not LLAMA_AVAILABLE:
        return None
    
    try:
        # Build context for the LLM
        schema = get_database_schema(db_path)
        metrics = get_available_metrics(registry)
        
        system_prompt = f"""You are a natural language to SQL intent parser for an educational analytics system.

Database Schema:
{schema}

Available Metrics:
{metrics}

Your task is to parse natural language questions and return a JSON object with:
- "metric": the exact metric name from the available metrics
- "params": a dictionary of required parameters

For module/assessment names, try to extract the name and I'll resolve it to an ID.

Examples:
- "How many students completed module 2?" → {{"metric": "students_completed_module", "params": {{"module_id": 2}}}}
- "How many students completed module Foundations?" → {{"metric": "students_completed_module", "params": {{"module_name": "Foundations"}}}}
- "What's the average score on assessment 3?" → {{"metric": "average_assessment_score", "params": {{"assessment_id": 3}}}}

Return ONLY the JSON object, no other text."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question}
        ]
        
        response = chat_llama(messages, temperature=0.0)
        
        # Try to parse the JSON response
        try:
            intent = json.loads(response.strip())
        except json.JSONDecodeError:
            # Try to extract JSON from response if there's extra text
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                intent = json.loads(json_match.group())
            else:
                return None
        
        # Resolve module/assessment names to IDs if needed
        params = intent.get("params", {})
        
        if "module_name" in params:
            module_id = extract_module_id_by_name(db_path, params["module_name"])
            if module_id:
                params["module_id"] = module_id
                del params["module_name"]
            else:
                return None  # Could not resolve module name
        
        if "assessment_name" in params:
            assessment_id = extract_assessment_id_by_name(db_path, params["assessment_name"])
            if assessment_id:
                params["assessment_id"] = assessment_id
                del params["assessment_name"]
            else:
                return None  # Could not resolve assessment name
        
        return intent
        
    except (LlamaClientError, Exception) as e:
        print(f"LLM parsing failed: {e}", file=sys.stderr)
        return None


def parse_question_with_fallback(question: str, registry, db_path: str) -> Optional[Dict[str, Any]]:
    """Parse question using LLM first, then fall back to rule-based parser."""
    # Try LLM parsing first
    if LLAMA_AVAILABLE:
        llm_result = llama_parse_question(question, registry, db_path)
        if llm_result:
            return llm_result
    
    # Fall back to rule-based parsing
    return rules_parse(question)

