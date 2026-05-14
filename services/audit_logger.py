"""
SQLite audit logger.
Persists every email action (generated or sent) for compliance and traceability.
"""

import sqlite3
import os
from datetime import datetime, date
from typing import List, Dict, Any

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "audit.db")


def _get_connection() -> sqlite3.Connection:
    """Return a connection, creating the table if it doesn't exist."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            invoice_no TEXT NOT NULL,
            amount_due REAL NOT NULL,
            stage TEXT NOT NULL,
            tone TEXT,
            send_status TEXT NOT NULL,
            dry_run INTEGER NOT NULL
        )
        """
    )
    conn.commit()
    return conn


def log_action(
    invoice_no: str,
    amount_due: float,
    stage: str,
    tone: str,
    send_status: str,
    dry_run: bool,
) -> int:
    """
    Insert an audit record and return the new row ID.
    """
    conn = _get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO audit_log (timestamp, invoice_no, amount_due, stage, tone, send_status, dry_run)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.utcnow().isoformat(),
                invoice_no,
                amount_due,
                stage,
                tone,
                send_status,
                int(dry_run),
            ),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_logs() -> List[Dict[str, Any]]:
    """Return every audit log entry, newest first."""
    conn = _get_connection()
    try:
        cursor = conn.execute(
            "SELECT id, timestamp, invoice_no, amount_due, stage, tone, send_status, dry_run "
            "FROM audit_log ORDER BY id DESC"
        )
        rows = cursor.fetchall()
        return [
            {
                "id": r[0],
                "timestamp": r[1],
                "invoice_no": r[2],
                "amount_due": r[3],
                "stage": r[4],
                "tone": r[5],
                "send_status": r[6],
                "dry_run": bool(r[7]),
            }
            for r in rows
        ]
    finally:
        conn.close()


def get_sent_today_count() -> int:
    """Return the number of emails sent (not dry-run) today."""
    conn = _get_connection()
    try:
        today_prefix = date.today().isoformat()
        cursor = conn.execute(
            "SELECT COUNT(*) FROM audit_log WHERE send_status = 'sent' AND timestamp LIKE ?",
            (f"{today_prefix}%",),
        )
        return cursor.fetchone()[0]
    finally:
        conn.close()
