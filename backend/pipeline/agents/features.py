"""Agent 2 - Feature Engineering: compute anomaly-detection features."""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from backend.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

FEATURE_NAMES: tuple[str, ...] = (
    "log_amount",
    "amount_zscore",
    "hour_risk",
    "is_transfer",
    "is_new_payee",
    "rolling_7d_spend",
    "payee_concentration",
    "amount_vs_rolling_mean",
)

TRANSFER_KEYWORDS: tuple[str, ...] = (
    "transfer",
    "wire",
    "crypto",
    "offshore",
    "western union",
)


def run(state: PipelineState) -> dict[str, list[list[float]] | list[str]]:
    """Compute feature matrix from cleaned transaction DataFrame."""
    df: pd.DataFrame = state["df"]
    n_rows: int = len(df)
    logger.info("Feature engineering on %d rows", n_rows)

    if n_rows == 0:
        return {"feature_matrix": [], "feature_names": list(FEATURE_NAMES)}

    amounts: np.ndarray = df["amount"].to_numpy(dtype=np.float64)
    log_amount: np.ndarray = np.log1p(amounts)
    amount_zscore: np.ndarray = _compute_amount_zscore(amounts)
    hour_risk: np.ndarray = _compute_hour_risk(df)
    is_transfer: np.ndarray = _compute_is_transfer(df)
    is_new_payee: np.ndarray = _compute_is_new_payee(df["payee"])
    rolling_7d_spend: np.ndarray = _compute_rolling_7d_spend(df)
    payee_concentration: np.ndarray = _compute_payee_concentration(df)
    amount_vs_rolling_mean: np.ndarray = np.clip(
        amounts / (rolling_7d_spend / 7.0 + 1e-9), 0.0, 50.0
    )

    feature_matrix: list[list[float]] = [
        [
            float(log_amount[i]),
            float(amount_zscore[i]),
            float(hour_risk[i]),
            float(is_transfer[i]),
            float(is_new_payee[i]),
            float(rolling_7d_spend[i]),
            float(payee_concentration[i]),
            float(amount_vs_rolling_mean[i]),
        ]
        for i in range(n_rows)
    ]

    logger.info("Feature engineering complete: %d features per row", len(FEATURE_NAMES))

    return {
        "feature_matrix": feature_matrix,
        "feature_names": list(FEATURE_NAMES),
    }


def _compute_amount_zscore(amounts: np.ndarray) -> np.ndarray:
    """Standardized amount, clipped to reduce outlier dominance."""
    zscore: np.ndarray = (amounts - np.mean(amounts)) / (np.std(amounts) + 1e-9)
    return np.clip(zscore, -3.0, 10.0)


def _compute_hour_risk(df: pd.DataFrame) -> np.ndarray:
    """Flag transactions outside 6am-9pm; default hour 12 when column absent."""
    if "hour_of_day" not in df.columns:
        hours: np.ndarray = np.full(len(df), 12.0, dtype=np.float64)
    else:
        hours = df["hour_of_day"].fillna(12).to_numpy(dtype=np.float64)

    return ((hours < 6) | (hours > 21)).astype(np.float64)


def _compute_is_transfer(df: pd.DataFrame) -> np.ndarray:
    """Flag transfer-category or exploitation-keyword payees."""
    has_category: bool = "category" in df.columns
    has_payee: bool = "payee" in df.columns
    if not has_category and not has_payee:
        return np.zeros(len(df), dtype=np.float64)

    result: np.ndarray = np.zeros(len(df), dtype=np.float64)

    if has_category:
        category_match: np.ndarray = (
            df["category"].astype(str).str.lower() == "transfer"
        ).to_numpy(dtype=np.float64)
        result = np.maximum(result, category_match)

    if has_payee:
        payees_lower: pd.Series = df["payee"].astype(str).str.lower()
        for keyword in TRANSFER_KEYWORDS:
            keyword_match: np.ndarray = payees_lower.str.contains(
                keyword, regex=False
            ).to_numpy(dtype=np.float64)
            result = np.maximum(result, keyword_match)

    return result


def _compute_is_new_payee(payees: pd.Series) -> np.ndarray:
    """Flag payees seen fewer than 2 times in all prior rows."""
    counts_before: dict[str, int] = {}
    result: np.ndarray = np.zeros(len(payees), dtype=np.float64)

    for i, payee in enumerate(payees):
        prior_count: int = counts_before.get(str(payee), 0)
        result[i] = 1.0 if prior_count < 2 else 0.0
        counts_before[str(payee)] = prior_count + 1

    return result


def _compute_rolling_7d_spend(df: pd.DataFrame) -> np.ndarray:
    """Sum of amounts in the 7-day window ending on each row's date."""
    rolling: pd.Series = df.set_index("date")["amount"].rolling("7D").sum()
    return rolling.fillna(0.0).to_numpy(dtype=np.float64)


def _compute_payee_concentration(df: pd.DataFrame) -> np.ndarray:
    """Fraction of total spend attributed to each row's payee."""
    total_spend: float = float(df["amount"].sum())
    if total_spend == 0.0:
        return np.zeros(len(df), dtype=np.float64)

    payee_totals: pd.Series = df.groupby("payee")["amount"].transform("sum")
    return (payee_totals / total_spend).to_numpy(dtype=np.float64)
