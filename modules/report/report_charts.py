# modules/report/report_charts.py
from __future__ import annotations

from .chart_config import CHARTS
from .chart_base import require_mpl, build_line_chart


def _period_text(df) -> str | None:
    if "date" not in df.columns or df.empty:
        return None
    start = str(df["date"].min())[:10]
    end = str(df["date"].max())[:10]
    return f"{start} ～ {end}"


# =========================================================
# P2: フィジカル（身長・体重）
# =========================================================
def fig_physical_height_weight(report, show_roadmap: bool = True):
    require_mpl()
    df = report.portfolio
    spec = CHARTS["physical_height_weight"]
    return build_line_chart(df, spec, period_text=_period_text(df), show_latest_annotation=True)


# =========================================================
# P2: 走力（50m / 1500m / 3000m）
# =========================================================
def fig_run_50m(report, show_roadmap: bool = True):
    require_mpl()
    df = report.portfolio
    spec = CHARTS["run_50m"]
    return build_line_chart(df, spec, period_text=_period_text(df), show_latest_annotation=True)


def fig_run_1500m(report, show_roadmap: bool = True):
    require_mpl()
    df = report.portfolio
    spec = CHARTS["run_1500m"]
    return build_line_chart(df, spec, period_text=_period_text(df), show_latest_annotation=True)


def fig_run_3000m(report, show_roadmap: bool = True):
    require_mpl()
    df = report.portfolio
    spec = CHARTS["run_3000m"]
    return build_line_chart(df, spec, period_text=_period_text(df), show_latest_annotation=True)


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    require_mpl()
    df = report.portfolio
    spec = CHARTS["academic_rank_dev"]
    return build_line_chart(df, spec, period_text=_period_text(df), show_latest_annotation=True)


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    require_mpl()
    df = report.portfolio
    spec = CHARTS["academic_rating_scores"]
    return build_line_chart(df, spec, period_text=_period_text(df), show_latest_annotation=True)
