"""
FastAPI entry point — routes, CORS, and middleware.
"""

import os
from typing import List, Dict, Any

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from models.schemas import (
    InvoiceComputed,
    EmailGenerationRequest,
    EmailGenerationResponse,
    SendEmailRequest,
)
from services.data_ingestion import parse_csv_file, parse_upload
from services.email_generator import generate_email
from services.email_sender import send_email
from services.audit_logger import log_action, get_all_logs, get_sent_today_count
from agents.email_agent import process_invoice_email

load_dotenv()

# ── App setup ───────────────────────────────────────────────────
app = FastAPI(
    title="Debt Recovery Email Automation",
    description="Automates overdue-invoice email generation with escalation stages, LLM drafting, and a full audit trail.",
    version="1.0.0",
)

FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
DEFAULT_CSV = os.path.join(DATA_DIR, "invoices.csv")


# ── Routes ──────────────────────────────────────────────────────


@app.get("/api/invoices", response_model=List[InvoiceComputed])
def get_invoices():
    """Parse the default invoices.csv and return records with computed stages."""
    try:
        return parse_csv_file(DEFAULT_CSV)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="invoices.csv not found in data/")
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))


@app.post("/api/upload", response_model=List[InvoiceComputed])
async def upload_file(file: UploadFile = File(...)):
    """Accept a CSV/Excel upload, sanitize it, and return enriched records."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file provided.")

    contents = await file.read()
    try:
        records = parse_upload(contents, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    # Persist the uploaded file as the new default dataset
    ext = file.filename.rsplit(".", 1)[-1].lower()
    save_path = os.path.join(DATA_DIR, f"invoices.{ext}")
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(save_path, "wb") as f:
        f.write(contents)

    return records


@app.post("/api/generate-email", response_model=EmailGenerationResponse)
def api_generate_email(req: EmailGenerationRequest):
    """Call Gemini to draft a tone-appropriate email for the given invoice."""
    invoice = req.invoice.model_dump()

    if invoice["stage"] == "Escalated":
        raise HTTPException(
            status_code=403,
            detail="Manual Review Required — automation blocked for escalated invoices (30+ days).",
        )
    if invoice["stage"] == "Current":
        raise HTTPException(
            status_code=400,
            detail="Invoice is not overdue; no recovery email needed.",
        )

    try:
        result = generate_email(invoice)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))

    return result


@app.post("/api/send-email")
def api_send_email(req: SendEmailRequest):
    """Send an email via SMTP (or dry-run) and log to audit trail."""
    invoice = req.invoice.model_dump()

    # ── Escalation cap: hard block ──────────────────────────────
    if invoice["stage"] == "Escalated":
        raise HTTPException(
            status_code=403,
            detail="Manual Review Required — sending is blocked for escalated invoices.",
        )

    status = send_email(
        to_email=invoice["customer_email"],
        subject=req.subject,
        body=req.body,
        dry_run=req.dry_run,
    )

    audit_id = log_action(
        invoice_no=invoice["invoice_no"],
        amount_due=invoice["amount_due"],
        stage=invoice["stage"],
        tone=invoice.get("tone", "Professional"), # Fallback if tone not explicitly in schema
        send_status=status,
        dry_run=req.dry_run,
    )

    return {
        "send_status": status,
        "audit_id": audit_id,
        "dry_run": req.dry_run,
    }


@app.get("/api/audit-log")
def api_audit_log():
    """Return the full audit history from the SQLite database."""
    return get_all_logs()


@app.get("/api/dashboard-stats")
def api_dashboard_stats():
    """
    Aggregate counts for the dashboard:
    - total invoices in the default CSV
    - overdue count (days_overdue > 0)
    - emails sent today (non-dry-run)
    """
    try:
        records = parse_csv_file(DEFAULT_CSV)
    except Exception:
        records = []

    total = len(records)
    overdue = sum(1 for r in records if r["days_overdue"] > 0)
    sent_today = get_sent_today_count()

    return {
        "total_invoices": total,
        "overdue_invoices": overdue,
        "sent_today": sent_today,
    }


# ── Convenience: full agent workflow in one call ────────────────


@app.post("/api/process-email")
def api_process_email(req: SendEmailRequest):
    """
    Convenience endpoint: generate + send + audit in a single call,
    delegating to the email agent.
    """
    invoice = req.invoice.model_dump()
    try:
        result = process_invoice_email(invoice, dry_run=req.dry_run)
    except (ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    return result
