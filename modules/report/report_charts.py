# modules/report/report_charts.py
"""
Figure builders for report module.

IMPORTANT:
- Keep this module import-light to avoid import-time crashes.
- Always return matplotlib Figure objects (do not call st.pyplot here).
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import pandas as pd

from .chart_base import build_line_chart
from .chart_config import CHARTS


def _records_to_df(report: Dict[str, Any]) -> pd.DataFrame:
    """
    report is expected to have:
      - report["records"]: list[dict] with at least {"date": "...", metrics...}
    """
    records = report.get("records") or []
    df = pd.DataFrame(records)
    if df.empty:
        return df
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
    return df


def _roadmap_to_df(report: Dict[str, Any]) -> pd.DataFrame:
    """
    roadmap is expected to be already expanded to rows with date + *_low/mid/high columns,
    OR a list of dicts in report["roadmap_records"].
    """
    rm = report.get("roadmap_records") or []
    df = pd.DataFrame(rm)
    if df.empty:
        return df
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        df = df.sort_values("date")
    return df


# -----------------------------
# Compatibility API (used by ui_report.py)
# -----------------------------
def fig_physical_height_weight_bmi(report: Dict[str, Any], show_roadmap: bool = True):
    """
    Compatibility wrapper.
    BMI is intentionally NOT plotted for now (per your decision).
    """
    df = _records_to_df(report)
    roadmap = _roadmap_to_df(report) if show_roadmap else None
    spec = CHARTS["physical_height_weight"]
    return build_line_chart(df, spec, period_text=report.get("period_text"), roadmap=roadmap)


def fig_run_metric(
    report: Dict[str, Any],
    metric: str,
    title: str,
    show_roadmap: bool = True,
    mmss: bool = False,
):
    """
    Generic runner. We map the metric to the corresponding ChartSpec.
    """
    # NOTE: We keep your compatibility rule:
    # UI says 50m but the column is run_100m_sec.
    if metric == "run_100m_sec":
        spec = CHARTS["run_50m"]
    elif metric == "run_1500m_sec":
        spec = CHARTS["run_1500m"]
    elif metric == "run_3000m_sec":
        spec = CHARTS["run_3000m"]
    else:
        # fallback: build a minimal spec? -> keep deterministic and strict:
        raise KeyError(f"Unsupported metric for fig_run_metric: {metric}")

    df = _records_to_df(report)
    roadmap = _roadmap_to_df(report) if show_roadmap else None

    # override title if needed
    if title and spec.title != title:
        spec = type(spec)(
            title=title,
            x_label=spec.x_label,
            date_col=spec.date_col,
            left_axis=spec.left_axis,
            right_axis=spec.right_axis,
            left_series=spec.left_series,
            right_series=spec.right_series,
            roadmap_base_color=spec.roadmap_base_color,
            roadmap_style=spec.roadmap_style,
        )

    return build_line_chart(df, spec, period_text=report.get("period_text"), roadmap=roadmap)


def fig_academic_rank_deviation(report: Dict[str, Any], show_roadmap: bool = True):
    df = _records_to_df(report)
    roadmap = _roadmap_to_df(report) if show_roadmap else None
    spec = CHARTS["academic_rank_dev"]
    return build_line_chart(df, spec, period_text=report.get("period_text"), roadmap=roadmap)


def fig_academic_rating_scores(report: Dict[str, Any], show_roadmap: bool = True):
    df = _records_to_df(report)
    roadmap = _roadmap_to_df(report) if show_roadmap else None
    spec = CHARTS["academic_rating_scores"]
    return build_line_chart(df, spec, period_text=report.get("period_text"), roadmap=roadmap)
