"""Agent 1 - Ingestion: load and clean transaction CSV."""

from __future__ import annotations

import logging

import pandas as pd

from backend.pipeline.state import PipelineState

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS: tuple[str, ...] = ("date", "amount", "payee")


def run(state: PipelineState) -> dict[str, pd.DataFrame | int]:
    """Load CSV from state file_path, validate columns, clean, and return df + row_count."""
    file_path: str = state["file_path"]
    logger.info("Ingesting CSV from %s", file_path)

    df: pd.DataFrame = pd.read_csv(file_path)

    missing: list[str] = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {', '.join(missing)}")

    cleaned_df: pd.DataFrame = df.copy()
    cleaned_df["date"] = pd.to_datetime(cleaned_df["date"], errors="coerce")
    cleaned_df["amount"] = cleaned_df["amount"].fillna(0.0)
    cleaned_df["payee"] = cleaned_df["payee"].fillna("Unknown")

    if "hour_of_day" in cleaned_df.columns:
        cleaned_df["hour_of_day"] = cleaned_df["hour_of_day"].fillna(12).astype(int)

    if "category" in cleaned_df.columns:
        cleaned_df["category"] = cleaned_df["category"].fillna("other")

    cleaned_df = cleaned_df.sort_values("date", ascending=True).reset_index(drop=True)

    row_count: int = len(cleaned_df)
    logger.info("Ingestion complete: %d rows", row_count)

    return {"df": cleaned_df, "row_count": row_count}
