"""Phase 1 thin-slice anomaly scorer. Replaced by LangGraph pipeline in Phase 2."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TypedDict

import numpy as np
import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI
from sklearn.ensemble import IsolationForest

load_dotenv(Path(__file__).parent.parent / ".env")

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS: tuple[str, ...] = ("date", "amount", "payee")
RISK_THRESHOLD: float = 65.0
NARRATIVE_UNAVAILABLE: str = (
    "Narrative unavailable - OPENAI_API_KEY not configured."
)


class PipelineResult(TypedDict):
    risk_score: float
    anomalous_indices: list[int]
    shap_features: list[dict]
    narrative: str
    alert_sent: bool


def run_pipeline(file_path: str, user_id: str) -> PipelineResult:
    """Score transaction risk from a CSV file."""
    _ = user_id  # reserved for Phase 2 personalization

    df = pd.read_csv(file_path)

    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    df = df.copy()
    df["amount"] = df["amount"].fillna(0.0)
    df["payee"] = df["payee"].fillna("Unknown")

    features = df[["amount"]].to_numpy()

    if len(features) == 0:
        return {
        "risk_score": 0.0,
        "anomalous_indices": [],
        "shap_features": [],
        "narrative": "",
        "alert_sent": False,
    }

    model = IsolationForest(contamination=0.05, random_state=42)
    model.fit(features)

    # decision_function: lower values indicate more anomalous points
    raw_scores = -model.decision_function(features)
    min_score = float(raw_scores.min())
    max_score = float(raw_scores.max())

    if max_score == min_score:
        normalized = np.zeros(len(raw_scores), dtype=float)
    else:
        normalized = (raw_scores - min_score) / (max_score - min_score) * 100.0

    risk_score = float(np.max(normalized))
    anomalous_indices = [int(i) for i in np.where(normalized > RISK_THRESHOLD)[0]]

    narrative = ""
    if risk_score > RISK_THRESHOLD:
        narrative = _generate_narrative(risk_score, anomalous_indices, file_path)

    return PipelineResult(
        risk_score=risk_score,
        anomalous_indices=anomalous_indices,
        shap_features=[],
        narrative=narrative,
        alert_sent=False,
    )


def _generate_narrative(
    risk_score: float,
    anomalous_indices: list[int],
    file_path: str,
) -> str:
    _ = file_path

    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key:
        return NARRATIVE_UNAVAILABLE

    num_anomalous = len(anomalous_indices)
    prompt = (
        "You are helping a family member understand financial monitoring results "
        "for an elderly loved one.\n\n"
        f"Risk score: {risk_score:.1f} out of 100\n"
        f"Number of flagged transactions: {num_anomalous}\n\n"
        "Write 3-4 warm, non-alarmist sentences explaining that unusual spending "
        "patterns were detected, what the family should do next (review the "
        "transactions and talk with their loved one in a caring way), and that "
        "this is an early heads-up, not a diagnosis. Do not make medical or legal "
        "claims. Avoid jargon. Use plain, caring language."
    )

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        content = response.choices[0].message.content
        return content if content is not None else NARRATIVE_UNAVAILABLE
    except Exception:
        logger.exception("Failed to generate narrative via OpenAI API")
        return NARRATIVE_UNAVAILABLE
