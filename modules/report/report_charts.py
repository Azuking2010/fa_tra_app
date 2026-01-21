# modules/report/report_charts.py
from __future__ import annotations

import pandas as pd

from .chart_base import build_line_chart
from .chart_config import CHARTS


def fig_physical_height_weight(df: pd.DataFrame, period_text: str = "", roadmap=None):
    """
    身長/体重（BMIは無し）
    df 想定カラム: date, height_cm, weight_kg
    roadmap: ym -> {height_cm_low/mid/high, weight_kg_low/mid/high, ...}
    """
    return build_line_chart(df, CHARTS["physical_height_weight"], period_text=period_text, roadmap=roadmap)


def fig_run_50m(df: pd.DataFrame, period_text: str = "", roadmap=None):
    """
    50m
    df 想定カラム: date, run_50m_sec
    """
    return build_line_chart(df, CHARTS["run_50m"], period_text=period_text, roadmap=roadmap)


def fig_run_1500m(df: pd.DataFrame, period_text: str = "", roadmap=None):
    """
    1500m
    df 想定カラム: date, run_1500m_sec
    """
    return build_line_chart(df, CHARTS["run_1500m"], period_text=period_text, roadmap=roadmap)


def fig_run_3000m(df: pd.DataFrame, period_text: str = "", roadmap=None):
    """
    3000m
    df 想定カラム: date, run_3000m_sec
    """
    return build_line_chart(df, CHARTS["run_3000m"], period_text=period_text, roadmap=roadmap)


def fig_academic_position(df: pd.DataFrame, period_text: str = "", roadmap=None):
    """
    順位/偏差値
    df 想定カラム: date, rank, deviation
    """
    return build_line_chart(df, CHARTS["academic_position"], period_text=period_text, roadmap=roadmap)


def fig_academic_scores_rating(df: pd.DataFrame, period_text: str = "", roadmap=None):
    """
    評点/教科スコア
    df 想定カラム: date, rating, score_jp, score_math, score_en, score_sci, score_soc
    """
    return build_line_chart(df, CHARTS["academic_scores_rating"], period_text=period_text, roadmap=roadmap)
