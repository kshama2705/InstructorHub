
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_conn(db_path: str):
    conn = sqlite3.connect(db_path)
    try:
        conn.execute("PRAGMA query_only = ON;")
        conn.execute("PRAGMA busy_timeout = 2000;")
        yield conn
    finally:
        conn.close()
