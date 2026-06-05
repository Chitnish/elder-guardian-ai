"""Alerts endpoint: list emergency contact notifications for a user."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db.supabase_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertItem(BaseModel):
    id: str
    contact_name: str
    contact_email: str
    contact_phone: str
    sms_status: str
    email_status: str
    sent_at: str


class AlertsResponse(BaseModel):
    alerts: list[AlertItem]


@router.get("/{user_id}", response_model=AlertsResponse)
async def get_alerts(user_id: str) -> AlertsResponse:
    client = get_client()

    try:
        response = (
            client.table("alerts")
            .select(
                "id, contact_name, contact_email, contact_phone, "
                "sms_status, email_status, sent_at"
            )
            .eq("user_id", user_id)
            .order("sent_at", desc=True)
            .limit(100)
            .execute()
        )

        alerts = [
            AlertItem(
                id=str(row["id"]),
                contact_name=str(row["contact_name"]),
                contact_email=str(row["contact_email"]),
                contact_phone=str(row["contact_phone"]),
                sms_status=str(row["sms_status"]),
                email_status=str(row["email_status"]),
                sent_at=str(row["sent_at"]),
            )
            for row in (response.data or [])
        ]

        return AlertsResponse(alerts=alerts)

    except Exception as e:
        logger.exception("Alerts fetch failed for user_id=%s", user_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "Database error", "detail": str(e)},
        ) from e
