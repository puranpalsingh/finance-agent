"""
Email agent — orchestrates the full workflow:
  1. Validate escalation stage (block if escalated).
  2. Call the LLM to generate a tone-appropriate email.
  3. Send (or dry-run) via SMTP.
  4. Log the action to the audit trail.
"""

from services.email_generator import generate_email
from services.email_sender import send_email
from services.audit_logger import log_action
from prompts.email_prompts import STAGE_PROMPTS


def process_invoice_email(invoice_data: dict, dry_run: bool = True) -> dict:
    """
    End-to-end email generation + dispatch + audit for a single invoice.

    Args:
        invoice_data: Enriched invoice dict (must include 'stage').
        dry_run: If True, email is drafted and logged but not dispatched.

    Returns:
        dict with keys: subject, body, send_status, audit_id, manual_review.
    """
    stage = invoice_data.get("stage", "")

    # ── Escalation cap: hard block ──────────────────────────────
    if stage == "Escalated":
        audit_id = log_action(
            invoice_no=invoice_data["invoice_no"],
            amount_due=invoice_data["amount_due"],
            stage=stage,
            tone="🚨 Manual Review",
            send_status="blocked_escalated",
            dry_run=dry_run,
        )
        return {
            "subject": None,
            "body": None,
            "send_status": "blocked_escalated",
            "audit_id": audit_id,
            "manual_review": True,
            "message": "Manual Review Required — this invoice has exceeded 30 days overdue.",
        }

    # ── Generate email via LLM ──────────────────────────────────
    email = generate_email(invoice_data)

    # ── Send or dry-run ─────────────────────────────────────────
    send_status = send_email(
        to_email=invoice_data["customer_email"],
        subject=email["subject"],
        body=email["body"],
        dry_run=dry_run,
    )

    # ── Audit log ───────────────────────────────────────────────
    audit_id = log_action(
        invoice_no=invoice_data["invoice_no"],
        amount_due=invoice_data["amount_due"],
        stage=stage,
        tone=STAGE_PROMPTS.get(stage, {}).get("tone", "Professional"),
        send_status=send_status,
        dry_run=dry_run,
    )

    return {
        "subject": email["subject"],
        "body": email["body"],
        "send_status": send_status,
        "audit_id": audit_id,
        "manual_review": False,
    }
