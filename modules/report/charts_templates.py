# modules/report/charts_templates.py
from __future__ import annotations

import pandas as pd

from .chart_base import build_line_chart
from .charts_definitions import CHARTS


def build_from_key(
    df: pd.DataFrame,
    key: str,
    period_text: str | None = None,
    roadmap_df: pd.DataFrame | None = None,
):
    spec = CHARTS[key]
    return build_line_chart(df, spec, period_text=period_text, roadmap_df=roadmap_df)
