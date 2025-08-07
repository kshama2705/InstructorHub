
from typing import Dict, Any
from db import get_conn

def execute_metric(db_path: str, sql: str, params: Dict[str, Any]):
    with get_conn(db_path) as conn:
        cur = conn.execute(sql, params)
        row = cur.fetchone()
        return None if row is None else row[0]
