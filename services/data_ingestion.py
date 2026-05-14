"""
Data ingestion service.
Parses CSV/Excel files, sanitizes inputs, and computes escalation stages.
"""

import re
import io
from datetime import datetime, date
from typing import List, Dict, Any

import pandas as pd


def _strip_html(value: Any) -> Any:
    """Remove all HTML tags from a string value to prevent injection."""
    if isinstance(value, str):
        return re.sub(r"<[^>]*>", "", value).strip()
    return value


def _compute_stage(days_overdue: int) -> str:
    """Map days overdue to an escalation stage string."""
    if days_overdue <= 0:
        return "Current"
    elif days_overdue <= 7:
        return "Stage 1"
    elif days_overdue <= 14:
        return "Stage 2"
    elif days_overdue <= 21:
        return "Stage 3"
    elif days_overdue <= 30:
        return "Stage 4"
    else:
        return "Escalated"


def _sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Strip HTML from every cell and normalize column names.
    """
    df.columns = [col.strip().lower().replace(" ", "_") for col in df.columns]
    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].apply(_strip_html)
    return df


def _enrich_with_stages(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Compute days_overdue and escalation stage for each row.
    Expects columns: invoice_no, customer_name, customer_email, amount_due, due_date.
    """
    required = {"invoice_no", "customer_name", "customer_email", "amount_due", "due_date"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    today = date.today()
    records: List[Dict[str, Any]] = []

    for _, row in df.iterrows():
        try:
            due = pd.to_datetime(row["due_date"]).date()
        except Exception:
            continue  # skip unparseable rows

        days_overdue = (today - due).days
        stage = _compute_stage(days_overdue)

        records.append(
            {
                "invoice_no": str(row["invoice_no"]),
                "customer_name": str(row["customer_name"]),
                "customer_email": str(row["customer_email"]),
                "amount_due": float(row["amount_due"]),
                "due_date": due.isoformat(),
                "days_overdue": days_overdue,
                "stage": stage,
            }
        )

    return records


def parse_csv_file(file_path: str) -> List[Dict[str, Any]]:
    """Load a CSV from disk, sanitize, and return enriched records."""
    df = pd.read_csv(file_path)
    df = _sanitize_dataframe(df)
    return _enrich_with_stages(df)


def parse_upload(contents: bytes, filename: str) -> List[Dict[str, Any]]:
    """
    Parse an uploaded CSV or Excel file from raw bytes.
    """
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext == "csv":
        df = pd.read_csv(io.BytesIO(contents))
    elif ext in ("xls", "xlsx"):
        df = pd.read_excel(io.BytesIO(contents))
    else:
        raise ValueError(f"Unsupported file type: .{ext}. Use .csv or .xlsx")

    df = _sanitize_dataframe(df)
    return _enrich_with_stages(df)
