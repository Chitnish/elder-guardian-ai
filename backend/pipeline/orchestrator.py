"""LangGraph orchestrator connecting all pipeline agents."""

from __future__ import annotations

import logging

import pandas as pd
from langgraph.graph import END, StateGraph

from backend.pipeline.agents.anomaly import run as anomaly_run
from backend.pipeline.agents.dispatch import run as dispatch_run
from backend.pipeline.agents.features import run as features_run
from backend.pipeline.agents.ingestion import run as ingestion_run
from backend.pipeline.agents.narrative import run as narrative_run
from backend.pipeline.simple_scorer import PipelineResult
from backend.pipeline.state import PipelineState

logger = logging.getLogger(__name__)


def should_alert(state: PipelineState) -> str:
    return "agent_narrative" if state["risk_score"] > 65 else END


graph = StateGraph(PipelineState)

graph.add_node("agent_ingestion", ingestion_run)
graph.add_node("agent_features", features_run)
graph.add_node("agent_anomaly", anomaly_run)
graph.add_node("agent_narrative", narrative_run)
graph.add_node("agent_dispatch", dispatch_run)

graph.set_entry_point("agent_ingestion")

graph.add_edge("agent_ingestion", "agent_features")
graph.add_edge("agent_features", "agent_anomaly")
graph.add_conditional_edges("agent_anomaly", should_alert)
graph.add_edge("agent_narrative", "agent_dispatch")
graph.add_edge("agent_dispatch", END)

pipeline = graph.compile()


def run_pipeline(file_path: str, user_id: str) -> PipelineResult:
    """Run the full LangGraph pipeline on a CSV file."""
    logger.info("Starting pipeline for user=%s file=%s", user_id, file_path)

    initial_state: PipelineState = {
        "file_path": file_path,
        "user_id": user_id,
        "df": pd.DataFrame(),
        "row_count": 0,
        "feature_matrix": [],
        "feature_names": [],
        "risk_score": 0.0,
        "anomalous_indices": [],
        "shap_features": [],
        "iso_forest_score": 0.0,
        "lstm_score": 0.0,
        "graph_score": 0.0,
        "narrative": "",
        "alert_sent": False,
    }

    final_state = pipeline.invoke(initial_state)

    logger.info(
        "Pipeline complete for user=%s risk_score=%.1f alert_sent=%s",
        user_id,
        final_state["risk_score"],
        final_state["alert_sent"],
    )

    return PipelineResult(
        risk_score=final_state["risk_score"],
        anomalous_indices=final_state["anomalous_indices"],
        shap_features=final_state["shap_features"],
        narrative=final_state["narrative"],
        alert_sent=final_state["alert_sent"],
    )
