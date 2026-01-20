# modules/report/report_charts.py
from __future__ import annotations

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False

from .chart_config import CHARTS
from .chart_base import (
    _require_mpl,
    setup_japanese_font,
    make_line_chart_single_axis,
    make_line_chart_dual_axis,
)


# =========================================================
# 既存と互換のため：必要最低限の公開関数を残す
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    """
    互換維持のため関数名はそのまま
    ※BMIは当面グラフに入れない（config側で身長/体重のみ）
    """
    _require_mpl()
    setup_japanese_font()

    spec = CHARTS["physical_hw"]
    df = report.portfolio
    return make_line_chart_dual_axis(report, df, spec, show_roadmap=show_roadmap)


def fig_run_metric(
    report,
    metric: str,
    title: str,
    show_roadmap: bool = True,
    mmss: bool = False,
):
    """
    互換維持用：
      既存コードがこの関数で 50/1500/3000 を呼んでいる可能性があるため残す。
    ただし、今後は chart_id で呼ぶのが安全。
    """
    _require_mpl()
    setup_japanese_font()

    # metric -> chart_id の解決（あなたのデータ列名に合わせて調整）
    # ここは「壊さない」ために柔軟に。
    metric_lower = (metric or "").lower()

    if "50" in metric_lower:
        chart_id = "run_50m"
    elif "1500" in metric_lower:
        chart_id = "run_1500m"
    elif "3000" in metric_lower:
        chart_id = "run_3000m"
    else:
        # 不明な場合は、従来通り単軸で秒表示の簡易グラフ
        df = report.portfolio
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(df["date"], df[metric], marker="o")
        ax.set_title(title)
        ax.set_ylabel("タイム（秒）")
        ax.grid(True, axis="y", alpha=0.3)
        return fig

    spec = CHARTS[chart_id]
    df = report.portfolio
    return make_line_chart_single_axis(report, df, spec, show_roadmap=show_roadmap)


def fig_academic_position(report, show_roadmap: bool = True):
    _require_mpl()
    setup_japanese_font()

    spec = CHARTS["academic_rank_dev"]
    df = report.portfolio
    return make_line_chart_dual_axis(report, df, spec, show_roadmap=show_roadmap)


def fig_academic_scores_rating(report, show_roadmap: bool = True):
    _require_mpl()
    setup_japanese_font()

    spec = CHARTS["academic_rating_scores"]
    df = report.portfolio
    return make_line_chart_dual_axis(report, df, spec, show_roadmap=show_roadmap)
