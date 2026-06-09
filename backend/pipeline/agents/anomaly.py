"""Agent 3 - Anomaly Detection: ensemble IF, LSTM AE, graph heuristics, and SHAP."""

from __future__ import annotations

import logging
from typing import Any

import numpy as np
import pandas as pd
import shap
import torch
import torch.nn as nn
from sklearn.ensemble import IsolationForest

from backend.pipeline.simple_scorer import (
    compute_anomalous_indices,
    compute_rule_score,
    ensemble_score,
    is_exploitation_payee,
)
from backend.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

IF_ANOMALY_THRESHOLD: float = 65.0


class LSTMAutoencoder(nn.Module):
    """Sequence autoencoder for per-row reconstruction error."""

    def __init__(self) -> None:
        super().__init__()
        self.encoder = nn.LSTM(input_size=8, hidden_size=16, batch_first=True)
        self.decoder = nn.LSTM(hidden_size=16, input_size=16, batch_first=True)
        self.output_layer = nn.Linear(16, 8)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Return per-timestep MSE reconstruction error, shape (batch, seq_len)."""
        encoded, _ = self.encoder(x)
        decoded, _ = self.decoder(encoded)
        reconstructed = self.output_layer(decoded)
        return ((x - reconstructed) ** 2).mean(dim=2)


def run(state: PipelineState) -> dict[str, Any]:
    """Score transaction risk via Isolation Forest, LSTM AE, graph heuristics, and SHAP."""
    df: pd.DataFrame = state["df"]
    feature_matrix_raw: list[list[float]] = state["feature_matrix"]
    feature_names: list[str] = state["feature_names"]
    n_rows: int = len(feature_matrix_raw)

    logger.info("Anomaly detection on %d rows", n_rows)

    empty_result: dict[str, Any] = {
        "risk_score": 0.0,
        "anomalous_indices": [],
        "shap_features": [],
        "iso_forest_score": 0.0,
        "lstm_score": 0.0,
        "graph_score": 0.0,
    }

    if n_rows == 0:
        return empty_result

    features: np.ndarray = np.asarray(feature_matrix_raw, dtype=np.float64)

    # PART 1 - Isolation Forest
    model = IsolationForest(contamination=0.08, random_state=42)
    model.fit(features)

    raw: np.ndarray = -model.decision_function(features)
    p10: float = float(np.percentile(raw, 10))
    p90: float = float(np.percentile(raw, 90))
    normalized: np.ndarray = np.clip(
        (raw - p10) / (p90 - p10 + 1e-9) * 100.0, 0.0, 100.0
    )
    if_score: float = float(np.percentile(normalized, 75))

    # PART 2 - LSTM Autoencoder
    lstm_score: float = 0.0
    if n_rows >= 5:
        try:
            lstm_score = _compute_lstm_score(features)
        except Exception:
            logger.exception("LSTM autoencoder scoring failed")
            lstm_score = 0.0

    # PART 3 - Graph scorer
    graph_score: float = _compute_graph_score(df)

    # PART 4 - SHAP on Isolation Forest
    shap_features: list[dict[str, float | str]] = []
    try:
        shap_features = _compute_shap_features(
            model, features, feature_names, normalized
        )
    except Exception:
        logger.exception("SHAP explanation failed")
        shap_features = []

    # PART 5 - Ensemble with rule-based hybrid
    exploit_mask: pd.Series = df.apply(
        lambda row: is_exploitation_payee(
            str(row.get("payee", "")),
            str(row.get("category", "")),
        ),
        axis=1,
    )
    rule_score: float = compute_rule_score(df, exploit_mask)
    risk_score: float = ensemble_score(if_score, rule_score)
    anomalous_indices: list[int] = compute_anomalous_indices(df, exploit_mask)

    logger.info(
        "Anomaly detection complete: risk_score=%.1f if=%.1f lstm=%.1f graph=%.1f",
        risk_score,
        if_score,
        lstm_score,
        graph_score,
    )

    return {
        "risk_score": risk_score,
        "anomalous_indices": anomalous_indices,
        "shap_features": shap_features,
        "iso_forest_score": if_score / 100.0,
        "lstm_score": lstm_score / 100.0,
        "graph_score": graph_score / 100.0,
    }


def _normalize_to_100(values: np.ndarray) -> np.ndarray:
    """Percentile-clipped normalization to 0-100."""
    p10 = float(np.percentile(values, 10))
    p90 = float(np.percentile(values, 90))
    return np.clip((values - p10) / (p90 - p10 + 1e-9) * 100.0, 0.0, 100.0)


def _compute_lstm_score(features: np.ndarray) -> float:
    """Run untrained LSTM AE; score = mean of top 10% reconstruction errors."""
    tensor = torch.tensor(features, dtype=torch.float32).unsqueeze(0)
    autoencoder = LSTMAutoencoder()
    autoencoder.eval()

    with torch.no_grad():
        errors: np.ndarray = autoencoder(tensor).squeeze(0).numpy()

    normalized_errors: np.ndarray = _normalize_to_100(errors)
    top_k: int = max(1, int(np.ceil(len(normalized_errors) * 0.1)))
    top_errors: np.ndarray = np.sort(normalized_errors)[-top_k:]
    return float(np.clip(float(np.mean(top_errors)), 0.0, 100.0))


def _compute_graph_score(df: pd.DataFrame) -> float:
    """Heuristic payee-pattern score without NetworkX."""
    payee_amounts: dict[str, list[float]] = {}
    for _, row in df.iterrows():
        payee: str = str(row["payee"])
        amount: float = float(row["amount"])
        payee_amounts.setdefault(payee, []).append(amount)

    sparse_high_total: float = 0.0
    single_large: float = 0.0

    for amounts in payee_amounts.values():
        count: int = len(amounts)
        total: float = float(sum(amounts))
        if 1 <= count <= 2 and total > 1000.0:
            sparse_high_total += 15.0
        if count == 1 and amounts[0] > 5000.0:
            single_large += 20.0

    graph_score: float = min(sparse_high_total, 60.0) + min(single_large, 40.0)
    return float(min(graph_score, 100.0))


def _compute_shap_features(
    model: IsolationForest,
    features: np.ndarray,
    feature_names: list[str],
    normalized_if: np.ndarray,
) -> list[dict[str, float | str]]:
    """Explain anomalous rows (IF score > 65) via TreeExplainer SHAP values."""
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(features)

    if isinstance(shap_values, list):
        shap_matrix: np.ndarray = np.asarray(shap_values[0])
    else:
        shap_matrix = np.asarray(shap_values)

    if shap_matrix.ndim == 3:
        shap_matrix = shap_matrix[:, :, 0]

    shap_features: list[dict[str, float | str]] = []
    anomalous_rows: np.ndarray = np.where(normalized_if > IF_ANOMALY_THRESHOLD)[0]

    for row_idx in anomalous_rows:
        row_shap: np.ndarray = shap_matrix[int(row_idx)]
        top_indices: np.ndarray = np.argsort(np.abs(row_shap))[-3:][::-1]
        for feat_idx in top_indices:
            shap_features.append(
                {
                    "feature": feature_names[int(feat_idx)],
                    "shap_value": float(row_shap[int(feat_idx)]),
                }
            )

    return shap_features
