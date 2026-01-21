# modules/report/chart_config.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional, Sequence, Tuple
import colorsys

from .chart_base import AxisSpec, SeriesSpec, ChartSpec, RoadmapBandSpec


# -------- Color helpers --------

def hex_to_rgb01(h: str) -> Tuple[float, float, float]:
    h = h.lstrip("#")
    return (int(h[0:2], 16) / 255.0, int(h[2:4], 16) / 255.0, int(h[4:6], 16) / 255.0)


def rgb01_to_hex(rgb: Tuple[float, float, float]) -> str:
    return "#{:02x}{:02x}{:02x}".format(
        int(max(0, min(1, rgb[0])) * 255),
        int(max(0, min(1, rgb[1])) * 255),
        int(max(0, min(1, rgb[2])) * 255),
    )


def shift_lightness(hex_color: str, delta: float) -> str:
    """
    delta: -0.3〜+0.3 くらいを想定
    """
    r, g, b = hex_to_rgb01(hex_color)
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = max(0.0, min(1.0, l + delta))
    rr, gg, bb = colorsys.hls_to_rgb(h, l, s)
    return rgb01_to_hex((rr, gg, bb))


# -------- Base palette（6色）--------
# 「提案してくれたカラーでOK」＝標準Tableau系で安定運用
PALETTE = [
    "#1f77b4",  # 1: blue
    "#ff7f0e",  # 2: orange
    "#2ca02c",  # 3: green
    "#d62728",  # 4: red
    "#9467bd",  # 5: purple
    "#8c564b",  # 6: brown
]


def c(i: int) -> str:
    return PALETTE[i - 1]


# -------- Chart specs --------

CHARTS: Dict[str, ChartSpec] = {
    # P2 フィジカル（身長/体重） BMIはいったん無し
    "physical_hw": ChartSpec(
        title="フィジカル推移（身長・体重）",
        left_axis=AxisSpec(ymin=160, ymax=190, major_step=2, minor_step=None, label="身長（cm）"),
        left_series=[
            SeriesSpec(col="height_cm", label="身長（cm）", color=c(1), lw=2.6),
        ],
        right_axis=AxisSpec(ymin=45, ymax=75, major_step=2, minor_step=None, label="体重（kg）"),
        right_series=[
            SeriesSpec(col="weight_kg", label="体重（kg）", color=c(2), lw=2.6),
        ],
        y_format="num",
    ),

    # P2 走力：50m（早いほど上＝9.0→5.0）
    "run_50m": ChartSpec(
        title="Run: 50m",
        left_axis=AxisSpec(ymin=9.0, ymax=5.0, major_step=0.25, minor_step=None, label="タイム（秒）"),
        left_series=[
            SeriesSpec(col="run_50m_sec", label="50m（秒）", color=c(1), lw=2.6),
        ],
        y_format="num",
    ),

    # P2 走力：1500m（5:00→4:00）補助10sec
    # 内部は「秒」で扱う（configも秒で定義）
    "run_1500m": ChartSpec(
        title="Run: 1500m",
        left_axis=AxisSpec(ymin=300, ymax=240, major_step=10, minor_step=None, label="タイム（分:秒）"),
        left_series=[
            SeriesSpec(col="run_1500m", label="1500m", color=c(1), lw=2.6),
        ],
        y_format="mmss",
    ),

    # P2 走力：3000m（10:30→9:30）補助10sec
    "run_3000m": ChartSpec(
        title="Run: 3000m",
        left_axis=AxisSpec(ymin=630, ymax=570, major_step=10, minor_step=None, label="タイム（分:秒）"),
        left_series=[
            SeriesSpec(col="run_3000m", label="3000m", color=c(1), lw=2.6),
        ],
        y_format="mmss",
    ),

    # P3 学業（順位/偏差値）
    "academic_rank_dev": ChartSpec(
        title="学業：順位・偏差値",
        left_axis=AxisSpec(ymin=50, ymax=0, major_step=5, minor_step=None, label="学年順位"),
        left_series=[
            SeriesSpec(col="rank_grade", label="学年順位", color=c(4), lw=2.6),
        ],
        right_axis=AxisSpec(ymin=30, ymax=80, major_step=5, minor_step=None, label="参考偏差値"),
        right_series=[
            SeriesSpec(col="deviation", label="偏差値", color=c(5), lw=2.6),
        ],
        y_format="num",
    ),

    # P3 学業（評点/教科スコア）
    "academic_scores": ChartSpec(
        title="学業：評点・教科スコア",
        left_axis=AxisSpec(ymin=0, ymax=5, major_step=0.5, minor_step=None, label="評点"),
        left_series=[
            SeriesSpec(col="rating", label="評点", color=c(3), lw=2.6),
        ],
        right_axis=AxisSpec(ymin=50, ymax=100, major_step=10, minor_step=None, label="教科スコア"),
        right_series=[
            # 教科は最大5色必要 → 2軸側に複数線
            SeriesSpec(col="score_jp", label="国語", color=c(1), lw=2.2),
            SeriesSpec(col="score_math", label="数学", color=c(2), lw=2.2),
            SeriesSpec(col="score_eng", label="英語", color=c(4), lw=2.2),
            SeriesSpec(col="score_sci", label="理科", color=c(5), lw=2.2),
            SeriesSpec(col="score_soc", label="社会", color=c(6), lw=2.2),
        ],
        y_format="num",
    ),
}
