"""Agent 4 - Narrative: generate a warm family-facing summary when risk is elevated."""

from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from backend.pipeline.state import PipelineState

load_dotenv(Path(__file__).parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

RISK_THRESHOLD: float = 65.0
NARRATIVE_UNAVAILABLE: str = (
    "Narrative unavailable - OPENAI_API_KEY not configured."
)
NARRATIVE_ERROR: str = (
    "Narrative unavailable - we could not generate a summary at this time."
)


def run(state: PipelineState) -> dict[str, str]:
    """Generate a caring narrative when risk_score exceeds the alert threshold."""
    risk_score: float = state["risk_score"]

    if risk_score <= RISK_THRESHOLD:
        logger.info("Risk score %.1f <= %.0f; skipping narrative", risk_score, RISK_THRESHOLD)
        return {"narrative": ""}

    api_key: str | None = os.getenv("OPENAI_API_KEY")
    if not api_key or not api_key.strip():
        logger.warning("OPENAI_API_KEY missing or empty; narrative unavailable")
        return {"narrative": NARRATIVE_UNAVAILABLE}

    anomalous_count: int = len(state["anomalous_indices"])
    prompt: str = _build_prompt(risk_score, anomalous_count, state["shap_features"])

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        content: str | None = response.choices[0].message.content
        if not content:
            logger.warning("OpenAI returned empty narrative content")
            return {"narrative": NARRATIVE_ERROR}
        logger.info("Narrative generated for risk_score=%.1f", risk_score)
        return {"narrative": content}
    except Exception:
        logger.exception("Failed to generate narrative via OpenAI API")
        return {"narrative": NARRATIVE_ERROR}


def _build_prompt(
    risk_score: float,
    anomalous_count: int,
    shap_features: list[dict[str, float]],
) -> str:
    """Assemble the user prompt from pipeline scoring outputs."""
    lines: list[str] = [
        "You are helping a family member understand financial monitoring results "
        "for an elderly loved one.",
        "",
        f"Risk score: {risk_score:.1f} out of 100",
        f"Number of flagged transactions: {anomalous_count}",
    ]

    top_features: list[str] = _top_shap_feature_names(shap_features, limit=3)
    if top_features:
        lines.append(f"Top risk factors: {', '.join(top_features)}")

    lines.extend(
        [
            "",
            "Write 3-4 warm, non-alarmist sentences explaining that unusual spending "
            "patterns were detected, what the family should do next (review the "
            "transactions and talk with their loved one in a caring way), and that "
            "this is an early heads-up, not a diagnosis. Do not make medical or legal "
            "claims. Avoid jargon. Use plain, caring language.",
        ]
    )
    return "\n".join(lines)


def _top_shap_feature_names(
    shap_features: list[dict[str, float]],
    limit: int,
) -> list[str]:
    """Return up to `limit` unique feature names ranked by absolute SHAP magnitude."""
    if not shap_features:
        return []

    ranked: list[tuple[str, float]] = []
    for entry in shap_features:
        feature_name: str = str(entry.get("feature", ""))
        shap_value: float = float(entry.get("shap_value", 0.0))
        if feature_name:
            ranked.append((feature_name, abs(shap_value)))

    ranked.sort(key=lambda item: item[1], reverse=True)

    seen: set[str] = set()
    top: list[str] = []
    for feature_name, _ in ranked:
        if feature_name in seen:
            continue
        seen.add(feature_name)
        top.append(feature_name)
        if len(top) >= limit:
            break
    return top
