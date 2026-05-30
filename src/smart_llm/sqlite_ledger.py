"""SQLite transactional shared state memory ledger (IPC Engine)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from datetime import datetime

def _get_db_connection(workspace_path: Path) -> sqlite3.Connection:
    """Open and return a transactional connection to the SQLite database."""
    out_dir = Path(workspace_path).resolve() / "smart-llm-out"
    out_dir.mkdir(exist_ok=True)
    db_path = out_dir / "ledger.db"
    
    conn = sqlite3.connect(str(db_path), timeout=10.0)
    # Enable WAL mode for high-concurrency read/write operations
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_ledger(workspace_path: Path) -> None:
    """Initialize the SQLite ledger table schemas."""
    conn = _get_db_connection(workspace_path)
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_ledger (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                alert_type TEXT,
                details TEXT,
                created_at TEXT
            )
        """)
    conn.close()

def set_state(workspace_path: Path, key: str, value: dict) -> None:
    """Perform an atomic UPSERT of state data in the ledger."""
    conn = _get_db_connection(workspace_path)
    value_json = json.dumps(value, ensure_ascii=False)
    timestamp = datetime.now().isoformat()
    
    try:
        # Use BEGIN IMMEDIATE to lock the DB for safe transactional concurrent writes
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("""
            INSERT INTO memory_ledger (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, value_json, timestamp))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_state(workspace_path: Path, key: str) -> dict | None:
    """Retrieve state data from the ledger."""
    conn = _get_db_connection(workspace_path)
    try:
        cursor = conn.execute("SELECT value FROM memory_ledger WHERE key = ?", (key,))
        row = cursor.fetchone()
        if row:
            return json.loads(row[0])
    finally:
        conn.close()
    return None

def raise_alert(workspace_path: Path, alert_type: str, details: dict) -> None:
    """Append a system alert entry to notify active agents."""
    conn = _get_db_connection(workspace_path)
    details_json = json.dumps(details, ensure_ascii=False)
    timestamp = datetime.now().isoformat()
    
    try:
        conn.execute("BEGIN IMMEDIATE;")
        conn.execute("""
            INSERT INTO system_alerts (alert_type, details, created_at)
            VALUES (?, ?, ?)
        """, (alert_type, details_json, timestamp))
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

def get_active_alerts(workspace_path: Path, limit: int = 5) -> list[dict]:
    """Retrieve latest active system alerts."""
    conn = _get_db_connection(workspace_path)
    results = []
    try:
        cursor = conn.execute(
            "SELECT id, alert_type, details, created_at FROM system_alerts ORDER BY id DESC LIMIT ?",
            (limit,)
        )
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "alert_type": row[1],
                "details": json.loads(row[2]),
                "created_at": row[3]
            })
    finally:
        conn.close()
    return results
