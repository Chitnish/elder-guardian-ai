"""CSV upload endpoint: persists file, runs risk pipeline, stores scores and alerts."""

from __future__ import annotations

import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import BaseModel

from backend.db.supabase_client import get_client
from backend.pipeline.simple_scorer import run_pipeline

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/upload", tags=["upload"])

RISK_ALERT_THRESHOLD: float = 65.0


class UploadResponse(BaseModel):
    upload_id: str
    risk_score: float
    anomalous_count: int
    narrative: str
    alert_sent: bool


@router.post("/", response_model=UploadResponse)
async def upload_csv(
    file: UploadFile,
    user_id: str = Form(...),
) -> UploadResponse:
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Invalid file type",
                "detail": "Only .csv files are accepted",
            },
        )

    upload_dir = Path(os.getenv("UPLOAD_DIR", "uploads"))
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest_path = upload_dir / f"{user_id}_{file.filename}"
    content = await file.read()
    dest_path.write_bytes(content)
    file_path = str(dest_path)

    upload_id: str | None = None
    client = get_client()

    try:
        insert_response = (
            client.table("uploads")
            .insert(
                {
                    "user_id": user_id,
                    "filename": file.filename,
                    "file_path": file_path,
                    "status": "processing",
                }
            )
            .execute()
        )
        upload_id = insert_response.data[0]["id"]

        result = run_pipeline(file_path, user_id)
        row_count = len(pd.read_csv(file_path))

        client.table("uploads").update(
            {"status": "complete", "row_count": row_count}
        ).eq("id", upload_id).execute()

        risk_score_response = (
            client.table("risk_scores")
            .insert(
                {
                    "user_id": user_id,
                    "upload_id": upload_id,
                    "score": result["risk_score"],
                    "iso_forest_score": result["risk_score"] / 100,
                    "shap_features": result["shap_features"],
                    "narrative": result["narrative"],
                }
            )
            .execute()
        )
        risk_score_id = risk_score_response.data[0]["id"]

        alert_sent = False
        if result["risk_score"] > RISK_ALERT_THRESHOLD:
            contacts_response = (
                client.table("emergency_contacts")
                .select("*")
                .eq("user_id", user_id)
                .limit(1)
                .execute()
            )
            if contacts_response.data:
                contact = contacts_response.data[0]
                client.table("alerts").insert(
                    {
                        "risk_score_id": risk_score_id,
                        "user_id": user_id,
                        "contact_name": contact["full_name"],
                        "contact_phone": contact["phone"],
                        "contact_email": contact["email"],
                        "sms_status": "mocked",
                        "email_status": "mocked",
                        "sent_at": datetime.utcnow().isoformat(),
                    }
                ).execute()
                alert_sent = True

        return UploadResponse(
            upload_id=upload_id,
            risk_score=result["risk_score"],
            anomalous_count=len(result["anomalous_indices"]),
            narrative=result["narrative"],
            alert_sent=alert_sent,
        )
    except Exception as e:
        logger.exception("Upload pipeline failed for user_id=%s", user_id)
        if upload_id is not None:
            client.table("uploads").update(
                {"status": "error", "error_message": str(e)}
            ).eq("id", upload_id).execute()
        raise HTTPException(
            status_code=500,
            detail={"error": "Pipeline failed", "detail": str(e)},
        ) from e
