# modules/report/report_charts.py
from __future__ import annotations

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False

from .charts_base import require_mpl, apply_jp_font
from .charts_definitions import (
    fig_physical_height_weight_bmi as _fig_physical_height_weight_bmi,
    fig_run_metric as _fig_run_metric,
    fig_academic_position as _fig_academic_position,
    fig_academic_scores_rating as _fig_academic_scores_rating,
)
from pathlib import Path
from .charts_base import apply_jp_font

# ここで確実に日本語フォントを適用（import時に毎回）
_FONT_PATH = Path(__file__).resolve().parents[2] / "assets" / "fonts" / "NotoSansJP-VariableFont_wght.ttf"
apply_jp_font(str(_FONT_PATH))


def _require_mpl():
    # 既存互換
    require_mpl()


# ここで日本語フォントを適用したい場合は、
# app.py もしくは report 描画の最初に apply_jp_font(...) を呼ぶのが理想。
# ただし「チャート側だけで完結」させたいなら、ここで呼んでもOK。
# apply_jp_font("assets/fonts/NotoSansJP-VariableFont_wght.ttf")


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    return _fig_physical_height_weight_bmi(report, show_roadmap=show_roadmap)


# =========================================================
# P2: 走力（50m / 1500m / 3000m）
# =========================================================
def fig_run_metric(
    report,
    metric: str,
    title: str,
    show_roadmap: bool = True,
    mmss: bool = False,
):
    return _fig_run_metric(report, metric=metric, title=title, show_roadmap=show_roadmap, mmss=mmss)


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    return _fig_academic_position(report, show_roadmap=show_roadmap)


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    return _fig_academic_scores_rating(report, show_roadmap=show_roadmap)
