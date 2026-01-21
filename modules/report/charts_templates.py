# modules/report/charts_templates.py
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from .chart_base import build_line_chart
from .charts_definitions import ChartSpec


def build_from_spec(
    df: pd.DataFrame,
    spec: ChartSpec,
    *,
    date_col: str = "date",
    period_text: str = "",
    roadmap: Optional[Dict[str, Any]] = None,
):
    """
    Thin wrapper to keep older call sites stable.
    """
    return build_line_chart(
        df=df,
        spec=spec,
        date_col=date_col,
        period_text=period_text,
        roadmap=roadmap,
    )
