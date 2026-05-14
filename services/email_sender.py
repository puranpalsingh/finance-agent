"""
Simulated email sender with dry-run logging.
All sends are simulated — no real SMTP connection is made.
Each "send" is logged to the console for verification.
"""

import logging
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def send_email(
    to_email: str,
    subject: str,
    body: str,
    dry_run: bool = True,
) -> str:
    """
    Simulate sending an email. Logs the action regardless of dry_run flag.

    Args:
        to_email: Recipient address.
        subject: Email subject line.
        body: Plain-text email body.
        dry_run: If True, status is 'dry_run'. If False, status is 'sent' (simulated).

    Returns:
        Status string: 'sent' (simulated) or 'dry_run'.
    """
    timestamp = datetime.utcnow().isoformat()
    status = "dry_run" if dry_run else "sent"

    logger.info(
        "\n"
        "═══════════════════════════════════════════════════\n"
        "  📧 SIMULATED EMAIL %s\n"
        "═══════════════════════════════════════════════════\n"
        "  Status   : %s\n"
        "  To       : %s\n"
        "  Subject  : %s\n"
        "  Time     : %s\n"
        "  Body Preview: %s...\n"
        "═══════════════════════════════════════════════════",
        "DRY RUN" if dry_run else "DISPATCH",
        status,
        to_email,
        subject,
        timestamp,
        body[:120].replace("\n", " "),
    )

    return status
