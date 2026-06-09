"""Agent 5 - Alert Dispatcher: notify emergency contacts when risk is elevated."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import resend
from dotenv import load_dotenv

from backend.db.supabase_client import get_client
from backend.pipeline.state import PipelineState

load_dotenv(Path(__file__).parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

RISK_THRESHOLD: float = 65.0


def run(state: PipelineState) -> dict[str, bool]:
    """Send SMS and email alerts to the user's emergency contact when risk is high."""
    risk_score: float = state["risk_score"]

    if risk_score <= RISK_THRESHOLD:
        logger.info(
            "Risk score %.1f <= %.0f; skipping alert dispatch",
            risk_score,
            RISK_THRESHOLD,
        )
        return {"alert_sent": False}

    client = get_client()
    response = (
        client.table("emergency_contacts")
        .select("*")
        .eq("user_id", state["user_id"])
        .limit(1)
        .execute()
    )

    if not response.data:
        logger.warning(
            "No emergency contact found for user_id=%s; alert not sent",
            state["user_id"],
        )
        return {"alert_sent": False}

    contact: dict[str, Any] = response.data[0]
    narrative: str = state.get("narrative", "")

    logger.info(
        "SMS alert (mocked): would send to %s - Risk score %.1f",
        contact["phone"],
        risk_score,
    )
    sms_status = "mocked"
    email_status: str = _send_email(risk_score, narrative, contact)

    try:
        client.table("alerts").insert(
            {
                "user_id": state["user_id"],
                "contact_name": contact["full_name"],
                "contact_phone": contact["phone"],
                "contact_email": contact["email"],
                "sms_status": sms_status,
                "email_status": email_status,
                "sent_at": datetime.utcnow().isoformat(),
            }
        ).execute()
    except Exception:
        logger.exception(
            "Failed to insert alert record for user_id=%s",
            state["user_id"],
        )
        return {"alert_sent": False}

    logger.info(
        "Alert dispatched for user_id=%s (sms=%s, email=%s)",
        state["user_id"],
        sms_status,
        email_status,
    )
    return {"alert_sent": True}


def _send_email(
    risk_score: float,
    narrative: str,
    contact: dict[str, Any],
) -> str:
    """Attempt Resend email delivery; return 'sent' or 'failed'."""
    resend_api_key: str | None = os.getenv("RESEND_API_KEY")
    from_email: str | None = os.getenv("RESEND_FROM_EMAIL")

    if not resend_api_key or not from_email:
        logger.warning(
            "Resend credentials missing; skipping email to %s",
            contact.get("email"),
        )
        return "failed"

    try:
        resend.api_key = resend_api_key
        resend.Emails.send(
            {
                "from": from_email,
                "to": contact["email"],
                "subject": f"Elder Guardian Alert - Risk Score {risk_score:.1f}",
                "html": (
                    f"<h2>Risk Alert</h2>"
                    f"<p><strong>Risk Score: {risk_score:.1f}/100</strong></p>"
                    f"<p>{narrative}</p>"
                    "<p><em>This is an early warning system. Please review recent "
                    "transactions and speak with your loved one.</em></p>"
                ),
            }
        )
        logger.info("Email alert sent to %s", contact["email"])
        return "sent"
    except Exception:
        logger.exception("Failed to send email alert to %s", contact.get("email"))
        return "failed"
