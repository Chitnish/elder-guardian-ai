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
EXPLOITATION_KEYWORDS: tuple[str, ...] = (
    "transfer",
    "wire",
    "crypto",
    "offshore",
    "western union",
)
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

    features = _build_feature_matrix(df)

    if len(features) == 0:
        return PipelineResult(
            risk_score=0.0,
            anomalous_indices=[],
            shap_features=[],
            narrative="",
            alert_sent=False,
        )

    if_score = _compute_if_score(features)

    exploit_mask = df.apply(
        lambda row: is_exploitation_payee(
            str(row.get("payee", "")),
            str(row.get("category", "")),
        ),
        axis=1,
    )

    rule_score = _compute_rule_score(df, exploit_mask)
    risk_score = _ensemble_score(if_score, rule_score)
    anomalous_indices = _compute_anomalous_indices(df, exploit_mask)

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


def _compute_if_score(features: np.ndarray) -> float:
    """Isolation Forest score normalized to 0-100 (75th percentile)."""
    model = IsolationForest(contamination=0.08, random_state=42)
    model.fit(features)

    # decision_function: more negative = more anomalous
    raw = -model.decision_function(features)
    p10 = float(np.percentile(raw, 10))
    p90 = float(np.percentile(raw, 90))
    normalized = np.clip((raw - p10) / (p90 - p10 + 1e-9) * 100.0, 0.0, 100.0)

    return float(np.percentile(normalized, 75))


def is_exploitation_payee(payee: str, category: str) -> bool:
    """Return True when payee or category matches exploitation keywords."""
    combined = (payee + " " + category).lower()
    return any(keyword in combined for keyword in EXPLOITATION_KEYWORDS)


def _compute_rule_score(df: pd.DataFrame, exploit_mask: pd.Series) -> float:
    """Rule-based exploitation score from 0-100."""
    if len(df) == 0:
        return 0.0

    exploit_total = float(df.loc[exploit_mask, "amount"].sum())
    total = float(df["amount"].sum())
    exploit_ratio = exploit_total / (total + 1e-9)
    rule_a = min(exploit_ratio * 120.0, 60.0)

    max_amount = float(df["amount"].max())
    if max_amount > 20000.0:
        rule_b = 35.0
    elif max_amount > 8000.0:
        rule_b = 25.0
    elif max_amount > 3000.0:
        rule_b = 15.0
    elif max_amount > 1000.0:
        rule_b = 8.0
    else:
        rule_b = 0.0

    if "hour_of_day" in df.columns:
        late_night = int((df["hour_of_day"] < 5).sum())
    else:
        late_night = 0
    rule_c = min(late_night * 8.0, 20.0)

    distinct_exploit_payees = int(df.loc[exploit_mask, "payee"].nunique())
    rule_d = min(distinct_exploit_payees * 8.0, 20.0)

    return float(min(rule_a + rule_b + rule_c + rule_d, 100.0))


def _ensemble_score(if_score: float, rule_score: float) -> float:
    """Blend isolation-forest and rule-based scores."""
    if rule_score > 15.0:
        final_score = 0.35 * if_score + 0.65 * rule_score
    else:
        final_score = 0.75 * if_score + 0.25 * rule_score

    return float(np.clip(final_score, 0.0, 100.0))


def _compute_anomalous_indices(
    df: pd.DataFrame, exploit_mask: pd.Series
) -> list[int]:
    """Flag exploitation-pattern and late-night transactions."""
    indices: set[int] = set(int(i) for i in np.where(exploit_mask.to_numpy())[0])

    if "hour_of_day" in df.columns:
        late_night_mask = (df["hour_of_day"] < 5).to_numpy()
        indices.update(int(i) for i in np.where(late_night_mask)[0])

    return sorted(indices)


def _build_feature_matrix(df: pd.DataFrame) -> np.ndarray:
    """Build anomaly-detection features for exploitation-pattern scoring."""
    amounts = df["amount"].to_numpy(dtype=float)
    log_amount = np.log1p(amounts)
    is_new_payee = _compute_is_new_payee(df["payee"])
    hour_risk = _compute_hour_risk(df)
    amount_zscore = _compute_amount_zscore(amounts)
    is_transfer = _compute_is_transfer(df)

    return np.column_stack(
        [log_amount, hour_risk, amount_zscore, is_transfer, is_new_payee]
    )


def _compute_is_new_payee(payees: pd.Series) -> np.ndarray:
    """Flag payees seen fewer than 3 times in all prior rows."""
    counts_before: dict[str, int] = {}
    result = np.zeros(len(payees), dtype=float)

    for i, payee in enumerate(payees):
        prior_count = counts_before.get(str(payee), 0)
        result[i] = 1.0 if prior_count < 3 else 0.0
        counts_before[str(payee)] = prior_count + 1

    return result


def _compute_hour_risk(df: pd.DataFrame) -> np.ndarray:
    """Flag late-night transactions (before 6am or after 9pm)."""
    if "hour_of_day" not in df.columns:
        return np.zeros(len(df), dtype=float)

    hours = df["hour_of_day"].fillna(12).to_numpy(dtype=float)
    return ((hours < 6) | (hours > 21)).astype(float)


def _compute_amount_zscore(amounts: np.ndarray) -> np.ndarray:
    """Standardized amount, clipped to reduce outlier dominance."""
    zscore = (amounts - np.mean(amounts)) / (np.std(amounts) + 1e-9)
    return np.clip(zscore, -3.0, 10.0)


def _compute_is_transfer(df: pd.DataFrame) -> np.ndarray:
    """Flag transfer-category transactions when category column is present."""
    if "category" not in df.columns:
        return np.zeros(len(df), dtype=float)

    return (df["category"].fillna("").astype(str).str.lower() == "transfer").astype(
        float
    ).to_numpy()


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
