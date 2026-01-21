# modules/report/chart_config.py
"""
Chart config (axis ranges, ticks, colors, roadmap styles).

This module should contain only plain data definitions.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


# -----------------------------
# Palette (base colors)
# -----------------------------
# You said: "色は提案してくれたカラーでOK"
# -> Here we define 6 base colors (RGB tuples).
BASE_COLORS: List[Tuple[int, int, int]] = [
    (31, 119, 180),   # 1: blue
    (255, 127, 14),   # 2: orange
    (44, 160, 44),    # 3: green
    (214, 39, 40),    # 4: red
    (148, 103, 189),  # 5: purple
    (140, 86, 75),    # 6: brown
]


def rgb01(rgb: Tuple[int, int, int]) -> Tuple[float, float, float]:
    return (rgb[0] / 255.0, rgb[1] / 255.0, rgb[2] / 255.0)


def adjust_brightness(rgb: Tuple[int, int, int], factor: float) -> Tuple[int, int, int]:
    """
    factor > 1.0 => brighter, factor < 1.0 => darker
    """
    r, g, b = rgb
    r = max(0, min(255, int(r * factor)))
    g = max(0, min(255, int(g * factor)))
    b = max(0, min(255, int(b * factor)))
    return (r, g, b)


# -----------------------------
# Spec data structures
# -----------------------------
@dataclass(frozen=True)
class SeriesSpec:
    key: str
    label: str
    color: Tuple[int, int, int]
    linewidth: float = 2.5


@dataclass(frozen=True)
class AxisSpec:
    label: str
    ylim: Tuple[float, float]
    major: float
    minor: float
    invert: bool = False
    mmss: bool = False  # for seconds->mm:ss formatting


@dataclass(frozen=True)
class RoadmapStyle:
    linewidth: float = 1.3
    linestyle: str = "--"  # thin dashed
    # low/mid/high brightness factors
    low_factor: float = 0.85
    mid_factor: float = 1.00
    high_factor: float = 1.15


@dataclass(frozen=True)
class ChartSpec:
    title: str
    x_label: str
    date_col: str
    left_axis: AxisSpec
    right_axis: Optional[AxisSpec]
    left_series: List[SeriesSpec]
    right_series: List[SeriesSpec]
    roadmap_base_color: Tuple[int, int, int] = BASE_COLORS[0]
    roadmap_style: RoadmapStyle = RoadmapStyle()


# -----------------------------
# Chart specifications
# -----------------------------
CHARTS: Dict[str, ChartSpec] = {
    # Physical: Height (left) + Weight (right), BMI removed for now.
    "physical_height_weight": ChartSpec(
        title="フィジカル推移（身長・体重）",
        x_label="",
        date_col="date",
        left_axis=AxisSpec(
            label="身長 (cm)",
            ylim=(160.0, 190.0),
            major=2.0,
            minor=2.0,
            invert=False,
            mmss=False,
        ),
        right_axis=AxisSpec(
            label="体重 (kg)",
            ylim=(45.0, 75.0),
            major=2.0,
            minor=2.0,
            invert=False,
            mmss=False,
        ),
        left_series=[
            SeriesSpec(key="height_cm", label="身長 (cm)", color=BASE_COLORS[0], linewidth=2.8),
        ],
        right_series=[
            SeriesSpec(key="weight_kg", label="体重 (kg)", color=BASE_COLORS[1], linewidth=2.8),
        ],
        roadmap_base_color=BASE_COLORS[0],
    ),

    # Run: 50m (stored as run_100m_sec for compatibility)
    "run_50m": ChartSpec(
        title="Run: 50m (stored as run_100m_sec)",
        x_label="",
        date_col="date",
        left_axis=AxisSpec(
            label="タイム (秒)",
            ylim=(9.0, 5.0),     # reversed: faster is higher
            major=0.5,
            minor=0.25,          # you requested 0.25
            invert=True,
            mmss=False,
        ),
        right_axis=None,
        left_series=[
            SeriesSpec(key="run_100m_sec", label="50m (秒)", color=BASE_COLORS[0], linewidth=2.8),
        ],
        right_series=[],
        roadmap_base_color=BASE_COLORS[0],
    ),

    # Run: 1500m (mm:ss)
    "run_1500m": ChartSpec(
        title="Run: 1500m",
        x_label="",
        date_col="date",
        left_axis=AxisSpec(
            label="タイム (分:秒)",
            ylim=(5 * 60 + 0, 4 * 60 + 0),  # 5:00 ~ 4:00
            major=10.0,
            minor=10.0,
            invert=True,
            mmss=True,
        ),
        right_axis=None,
        left_series=[
            SeriesSpec(key="run_1500m_sec", label="1500m", color=BASE_COLORS[2], linewidth=2.8),
        ],
        right_series=[],
        roadmap_base_color=BASE_COLORS[2],
    ),

    # Run: 3000m (mm:ss)
    "run_3000m": ChartSpec(
        title="Run: 3000m",
        x_label="",
        date_col="date",
        left_axis=AxisSpec(
            label="タイム (分:秒)",
            ylim=(10 * 60 + 30, 9 * 60 + 30),  # 10:30 ~ 9:30
            major=10.0,
            minor=10.0,
            invert=True,
            mmss=True,
        ),
        right_axis=None,
        left_series=[
            SeriesSpec(key="run_3000m_sec", label="3000m", color=BASE_COLORS[3], linewidth=2.8),
        ],
        right_series=[],
        roadmap_base_color=BASE_COLORS[3],
    ),

    # Academic: rank (left) + deviation (right)
    "academic_rank_dev": ChartSpec(
        title="学業推移（順位・偏差値）",
        x_label="",
        date_col="date",
        left_axis=AxisSpec(
            label="学年順位",
            ylim=(50.0, 0.0),  # smaller is better -> higher
            major=5.0,
            minor=5.0,
            invert=True,
            mmss=False,
        ),
        right_axis=AxisSpec(
            label="偏差値",
            ylim=(30.0, 80.0),
            major=5.0,
            minor=5.0,
            invert=False,
            mmss=False,
        ),
        left_series=[
            SeriesSpec(key="rank", label="学年順位", color=BASE_COLORS[4], linewidth=2.8),
        ],
        right_series=[
            SeriesSpec(key="deviation", label="偏差値", color=BASE_COLORS[5], linewidth=2.8),
        ],
        roadmap_base_color=BASE_COLORS[4],
    ),

    # Academic: rating (left) + subject scores (right)
    "academic_rating_scores": ChartSpec(
        title="学業推移（評点・教科スコア）",
        x_label="",
        date_col="date",
        left_axis=AxisSpec(
            label="評点",
            ylim=(0.0, 5.0),
            major=0.5,
            minor=0.5,
            invert=False,
            mmss=False,
        ),
        right_axis=AxisSpec(
            label="教科得点",
            ylim=(50.0, 100.0),
            major=10.0,
            minor=10.0,
            invert=False,
            mmss=False,
        ),
        left_series=[
            SeriesSpec(key="rating", label="評点", color=BASE_COLORS[0], linewidth=2.8),
        ],
        right_series=[
            SeriesSpec(key="score_jp", label="国語", color=BASE_COLORS[1], linewidth=2.5),
            SeriesSpec(key="score_math", label="数学", color=BASE_COLORS[2], linewidth=2.5),
            SeriesSpec(key="score_eng", label="英語", color=BASE_COLORS[3], linewidth=2.5),
            SeriesSpec(key="score_sci", label="理科", color=BASE_COLORS[4], linewidth=2.5),
            SeriesSpec(key="score_soc", label="社会", color=BASE_COLORS[5], linewidth=2.5),
        ],
        roadmap_base_color=BASE_COLORS[0],
    ),
}
