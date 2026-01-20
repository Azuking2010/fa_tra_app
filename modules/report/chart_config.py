# modules/report/chart_config.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


# =========================================================
# 色（tab色でFIX）
# =========================================================
BASE_COLORS = {
    "C1": "tab:blue",
    "C2": "tab:orange",
    "C3": "tab:green",
    "C4": "tab:red",
    "C5": "tab:purple",
    "C6": "tab:brown",
}

# ROADMAPの明暗（HSVで明度だけ上下させる想定）
ROADMAP_SHADE = {
    "low": 0.75,   # やや暗い
    "mid": 1.00,   # そのまま
    "high": 1.25,  # やや明るい（最大1.0でクリップ）
}

# ROADMAPの線スタイル（共通）
ROADMAP_STYLE = {
    "linestyle": "--",
    "linewidth": 1.3,
    "alpha": 0.65,
}


# =========================================================
# 軸設定のConfig
# =========================================================
@dataclass(frozen=True)
class AxisSpec:
    ymin: float
    ymax: float
    step: float
    invert: bool = False
    label: str = ""


@dataclass(frozen=True)
class SeriesSpec:
    col: str
    label: str
    color_key: str  # BASE_COLORS のキー（C1..C6）
    linestyle: str = "-"
    linewidth: float = 2.0
    marker: Optional[str] = "o"


@dataclass(frozen=True)
class ChartSpec:
    chart_id: str
    title: str
    x_col: str
    left_axis: AxisSpec
    series_left: List[SeriesSpec]
    right_axis: Optional[AxisSpec] = None
    series_right: Optional[List[SeriesSpec]] = None
    # mm:ss 表示にするか（y値は秒のまま）
    y_mmss: bool = False
    # 最新値注釈を入れるか（系列ごと）
    annotate_last: bool = True


# =========================================================
# チャート定義（FIX仕様）
# =========================================================
CHARTS: Dict[str, ChartSpec] = {
    # ---- P2: 身長・体重（BMIは当面なし） ----
    "physical_hw": ChartSpec(
        chart_id="physical_hw",
        title="フィジカル推移（身長・体重）",
        x_col="date",
        left_axis=AxisSpec(ymin=160, ymax=190, step=2, invert=False, label="身長（cm）"),
        series_left=[
            SeriesSpec(col="height_cm", label="身長（cm）", color_key="C1", marker="o"),
        ],
        right_axis=AxisSpec(ymin=45, ymax=75, step=2, invert=False, label="体重（kg）"),
        series_right=[
            SeriesSpec(col="weight_kg", label="体重（kg）", color_key="C2", marker="o"),
        ],
        y_mmss=False,
        annotate_last=True,
    ),

    # ---- P2: 走力（50m：速いほど上） ----
    "run_50m": ChartSpec(
        chart_id="run_50m",
        title="走力：50m",
        x_col="date",
        left_axis=AxisSpec(ymin=9.0, ymax=5.0, step=0.25, invert=False, label="タイム（秒）"),
        series_left=[
            SeriesSpec(col="run_50m_sec", label="50m（秒）", color_key="C1", marker="o"),
        ],
        y_mmss=False,
        annotate_last=True,
    ),

    # ---- P2: 走力（1500m：mm:ss、速いほど上） ----
    "run_1500m": ChartSpec(
        chart_id="run_1500m",
        title="走力：1500m",
        x_col="date",
        left_axis=AxisSpec(ymin=300, ymax=240, step=10, invert=False, label="タイム（分:秒）"),
        series_left=[
            SeriesSpec(col="run_1500m_sec", label="1500m（分:秒）", color_key="C1", marker="o"),
        ],
        y_mmss=True,
        annotate_last=True,
    ),

    # ---- P2: 走力（3000m：mm:ss、速いほど上） ----
    "run_3000m": ChartSpec(
        chart_id="run_3000m",
        title="走力：3000m",
        x_col="date",
        left_axis=AxisSpec(ymin=630, ymax=570, step=10, invert=False, label="タイム（分:秒）"),
        series_left=[
            SeriesSpec(col="run_3000m_sec", label="3000m（分:秒）", color_key="C1", marker="o"),
        ],
        y_mmss=True,
        annotate_last=True,
    ),

    # ---- P3: 学業（順位/偏差値） ----
    "academic_rank_dev": ChartSpec(
        chart_id="academic_rank_dev",
        title="学業：学年順位・偏差値（参考）",
        x_col="date",
        left_axis=AxisSpec(ymin=50, ymax=0, step=5, invert=False, label="学年順位（小さいほど上位）"),
        series_left=[
            SeriesSpec(col="rank", label="学年順位", color_key="C4", marker="o"),
        ],
        right_axis=AxisSpec(ymin=30, ymax=80, step=5, invert=False, label="偏差値（参考）"),
        series_right=[
            SeriesSpec(col="deviation", label="偏差値（参考）", color_key="C1", marker="o"),
        ],
        y_mmss=False,
        annotate_last=True,
    ),

    # ---- P3: 学業（評点/教科得点） ----
    "academic_rating_scores": ChartSpec(
        chart_id="academic_rating_scores",
        title="学業：評点・教科得点",
        x_col="date",
        left_axis=AxisSpec(ymin=0, ymax=5, step=0.5, invert=False, label="評点"),
        series_left=[
            SeriesSpec(col="rating", label="評点", color_key="C6", marker="o", linewidth=2.5),
        ],
        right_axis=AxisSpec(ymin=50, ymax=100, step=10, invert=False, label="得点（学力テスト）"),
        series_right=[
            SeriesSpec(col="score_jp", label="国語", color_key="C1", marker="o"),
            SeriesSpec(col="score_math", label="数学", color_key="C2", marker="o"),
            SeriesSpec(col="score_en", label="英語", color_key="C3", marker="o"),
            SeriesSpec(col="score_sci", label="理科", color_key="C4", marker="o"),
            SeriesSpec(col="score_soc", label="社会", color_key="C5", marker="o"),
        ],
        y_mmss=False,
        annotate_last=True,
    ),
}
