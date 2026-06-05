"""Dashboard endpoint: aggregated risk scores, alerts, and upload status."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.db.supabase_client import get_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


class RiskScoreItem(BaseModel):
    id: str
    score: float
    narrative: str
    scored_at: str


class AlertItem(BaseModel):
    id: str
    contact_name: str
    sms_status: str
    email_status: str
    sent_at: str


class DashboardResponse(BaseModel):
    risk_scores: list[RiskScoreItem]
    alerts: list[AlertItem]
    latest_upload_status: str | None


@router.get("/{user_id}", response_model=DashboardResponse)
async def get_dashboard(user_id: str) -> DashboardResponse:
    client = get_client()

    try:
        risk_scores_response = (
            client.table("risk_scores")
            .select("id, score, narrative, scored_at")
            .eq("user_id", user_id)
            .order("scored_at", desc=True)
            .limit(90)
            .execute()
        )

        if not risk_scores_response.data:
            raise HTTPException(
                status_code=404,
                detail={"error": "No data found for this user"},
            )

        alerts_response = (
            client.table("alerts")
            .select("id, contact_name, sms_status, email_status, sent_at")
            .eq("user_id", user_id)
            .order("sent_at", desc=True)
            .limit(50)
            .execute()
        )

        uploads_response = (
            client.table("uploads")
            .select("status")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        latest_upload_status: str | None = None
        if uploads_response.data:
            latest_upload_status = uploads_response.data[0].get("status")

        risk_scores = [
            RiskScoreItem(
                id=str(row["id"]),
                score=float(row["score"]),
                narrative=str(row["narrative"]),
                scored_at=str(row["scored_at"]),
            )
            for row in risk_scores_response.data
        ]

        alerts = [
            AlertItem(
                id=str(row["id"]),
                contact_name=str(row["contact_name"]),
                sms_status=str(row["sms_status"]),
                email_status=str(row["email_status"]),
                sent_at=str(row["sent_at"]),
            )
            for row in (alerts_response.data or [])
        ]

        return DashboardResponse(
            risk_scores=risk_scores,
            alerts=alerts,
            latest_upload_status=latest_upload_status,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Dashboard fetch failed for user_id=%s", user_id)
        raise HTTPException(
            status_code=500,
            detail={"error": "Database error", "detail": str(e)},
        ) from e
