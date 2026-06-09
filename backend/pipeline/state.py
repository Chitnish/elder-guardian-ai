"""Shared LangGraph pipeline state."""

from typing import TypedDict

import pandas as pd


class PipelineState(TypedDict):
    # Set by orchestrator before pipeline starts
    file_path: str
    user_id: str

    # Set by Agent 1 - Ingestion
    df: pd.DataFrame  # cleaned DataFrame
    row_count: int

    # Set by Agent 2 - Feature Engineering
    feature_matrix: list[list[float]]  # each inner list is one row's features
    feature_names: list[str]

    # Set by Agent 3 - Anomaly Detection
    risk_score: float
    anomalous_indices: list[int]
    shap_features: list[dict[str, float]]
    iso_forest_score: float
    lstm_score: float
    graph_score: float

    # Set by Agent 4 - Narrative
    narrative: str

    # Set by Agent 5 - Dispatch
    alert_sent: bool
