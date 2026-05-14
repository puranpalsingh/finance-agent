"""
Gemini 1.5 Flash integration for email generation.
Uses strict JSON response mode to guarantee parseable output.
"""

import json
import os

import google.generativeai as genai
from dotenv import load_dotenv

from prompts.email_prompts import STAGE_PROMPTS, GUARDRAIL_INSTRUCTION, build_prompt

load_dotenv()

_API_KEY = os.getenv("GEMINI_API_KEY", "")


def _get_model(system_instruction: str = None):
    """Configure and return a Gemini GenerativeModel instance."""
    if not _API_KEY:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")
    genai.configure(api_key=_API_KEY)
    return genai.GenerativeModel("gemini-flash-latest", system_instruction=system_instruction)


def generate_email(invoice_data: dict) -> dict:
    """
    Generate a debt-recovery email for the given invoice.

    Args:
        invoice_data: dict with keys invoice_no, customer_name, customer_email,
                      amount_due, due_date, days_overdue, stage.

    Returns:
        dict with 'subject' and 'body' keys.

    Raises:
        ValueError: if the stage is 'Escalated' or 'Current'.
        RuntimeError: on LLM / parsing failures.
    """
    stage = invoice_data.get("stage", "")

    if stage == "Escalated":
        raise ValueError(
            "Manual Review Required — automation is blocked for escalated invoices (30+ days overdue)."
        )
    if stage == "Current":
        raise ValueError("Invoice is not overdue; no recovery email needed.")

    stage_config = STAGE_PROMPTS.get(stage)
    if not stage_config:
        raise ValueError(f"Unknown escalation stage: {stage}")

    system_instruction = stage_config["system_instruction"] + GUARDRAIL_INSTRUCTION
    user_prompt = build_prompt(stage, invoice_data)

    model = _get_model(system_instruction=system_instruction)

    response = model.generate_content(
        user_prompt,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            temperature=0.4,
        ),
    )

    # Parse the strict-JSON response
    try:
        result = json.loads(response.text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"LLM returned invalid JSON: {exc}\nRaw: {response.text}")

    if "subject" not in result or "body" not in result:
        raise RuntimeError(
            f"LLM response missing required keys. Got: {list(result.keys())}"
        )

    return {"subject": result["subject"], "body": result["body"]}
