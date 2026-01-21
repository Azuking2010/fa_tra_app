# modules/report/report_charts.py
from __future__ import annotations

from .chart_base import build_line_chart
from .chart_config import CHARTS


def fig_physical_hw(df, period_text: str | None = None):
    """
    df 必須列:
      - date
      - height_cm
      - weight_kg
    """
    return build_line_chart(df, CHARTS["physical_hw"], period_text=period_text)


def fig_run_50m(df, period_text: str | None = None):
    """
    df 必須列:
      - date
      - run_50m_sec
    """
    return build_line_chart(df, CHARTS["run_50m"], period_text=period_text)


def fig_run_1500m(df, period_text: str | None = None):
    """
    df 必須列:
      - date
      - run_1500m   ( "4:54" 文字列でもOK / 数値でもOK )
    """
    return build_line_chart(df, CHARTS["run_1500m"], period_text=period_text)


def fig_run_3000m(df, period_text: str | None = None):
    """
    df 必須列:
      - date
      - run_3000m   ( "10:39" 文字列でもOK / 数値でもOK )
    """
    return build_line_chart(df, CHARTS["run_3000m"], period_text=period_text)


def fig_academic_rank_dev(df, period_text: str | None = None):
    """
    df 必須列:
      - date
      - rank_grade
      - deviation
    """
    return build_line_chart(df, CHARTS["academic_rank_dev"], period_text=period_text)


def fig_academic_scores(df, period_text: str | None = None):
    """
    df 必須列:
      - date
      - rating
      - score_jp / score_math / score_eng / score_sci / score_soc
    """
    return build_line_chart(df, CHARTS["academic_scores"], period_text=period_text)
