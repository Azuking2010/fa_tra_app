# modules/report/report_charts.py
from __future__ import annotations

import pandas as pd

from .charts_templates import build_from_key


def fig_physical(df: pd.DataFrame, period_text: str | None = None, roadmap_df: pd.DataFrame | None = None):
    return build_from_key(df, "height_weight", period_text=period_text, roadmap_df=roadmap_df)


def fig_run_50m(df: pd.DataFrame, period_text: str | None = None, roadmap_df: pd.DataFrame | None = None):
    return build_from_key(df, "run_50m", period_text=period_text, roadmap_df=roadmap_df)


def fig_run_1500m(df: pd.DataFrame, period_text: str | None = None, roadmap_df: pd.DataFrame | None = None):
    return build_from_key(df, "run_1500m", period_text=period_text, roadmap_df=roadmap_df)


def fig_run_3000m(df: pd.DataFrame, period_text: str | None = None, roadmap_df: pd.DataFrame | None = None):
    return build_from_key(df, "run_3000m", period_text=period_text, roadmap_df=roadmap_df)


def fig_academic_rank_dev(df: pd.DataFrame, period_text: str | None = None, roadmap_df: pd.DataFrame | None = None):
    return build_from_key(df, "academic_rank_dev", period_text=period_text, roadmap_df=roadmap_df)


def fig_academic_scores(df: pd.DataFrame, period_text: str | None = None, roadmap_df: pd.DataFrame | None = None):
    return build_from_key(df, "academic_scores", period_text=period_text, roadmap_df=roadmap_df)
