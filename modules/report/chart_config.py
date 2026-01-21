# modules/report/chart_config.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Tuple, Union

Color = Union[str, Tuple[float, float, float]]  # hex or RGB(0-1)


def _clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def adjust_color_rgb(rgb: Tuple[float, float, float], factor: float) -> Tuple[float, float, float]:
    """
    factor < 1.0 => darker
    factor > 1.0 => lighter
    """
    r, g, b = rgb
    return (_clamp01(r * factor), _clamp01(g * factor), _clamp01(b * factor))


def hex_to_rgb01(hex_color: str) -> Tuple[float, float, float]:
    h = hex_color.lstrip("#")
    if len(h) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b)


def rgb01_to_hex(rgb: Tuple[float, float, float]) -> str:
    r, g, b = rgb
    return "#{:02x}{:02x}{:02x}".format(int(_clamp01(r) * 255), int(_clamp01(g) * 255), int(_clamp01(b) * 255))


@dataclass(frozen=True)
class AxisConfig:
    label: str
    ymin: float
    ymax: float
    major_step: float
    invert: bool = False
    formatter: Optional[str] = None  # "sec_to_mmss" など


@dataclass(frozen=True)
class SeriesSpec:
    col: str
    label: str
    color_index: int  # 1-based
    axis: str = "left"  # "left" or "right"
    linewidth: float = 2.2
    marker: str = "o"


@dataclass(frozen=True)
class RoadmapSpec:
    # 例: col="height_cm" なら roadmapの "height_cm_low/mid/high" を参照
    col: str
    axis: str = "left"  # "left" or "right"
    style: str = "--"
    linewidth: float = 1.2
    alpha: float = 0.85
    # midは基本色、lowは暗め、highは明るめ
    low_factor: float = 0.75
    mid_factor: float = 1.00
    high_factor: float = 1.25


@dataclass(frozen=True)
class ChartSpec:
    title: str
    date_col: str = "date"
    left_axis: AxisConfig = None  # type: ignore
    right_axis: Optional[AxisConfig] = None
    series: List[SeriesSpec] = None  # type: ignore
    roadmap: Optional[List[RoadmapSpec]] = None


# =========
# 色（基本6色）
# =========
# Matplotlib tab10 をベースにした“見分けやすい”6色
BASE_COLORS_HEX: Dict[int, str] = {
    1: "#1f77b4",  # blue
    2: "#ff7f0e",  # orange
    3: "#2ca02c",  # green
    4: "#d62728",  # red
    5: "#9467bd",  # purple
    6: "#8c564b",  # brown
}


def get_base_color(idx: int) -> Tuple[float, float, float]:
    return hex_to_rgb01(BASE_COLORS_HEX[idx])


def get_roadmap_color(idx: int, kind: str, low_factor: float, mid_factor: float, high_factor: float) -> Tuple[float, float, float]:
    base = get_base_color(idx)
    if kind == "low":
        return adjust_color_rgb(base, low_factor)
    if kind == "high":
        return adjust_color_rgb(base, high_factor)
    return adjust_color_rgb(base, mid_factor)


# =========
# チャート定義（FIXした仕様）
# =========
CHARTS: Dict[str, ChartSpec] = {
    # 身長/体重（BMIは一旦無し）
    "physical_height_weight": ChartSpec(
        title="フィジカル推移（身長・体重）",
        left_axis=AxisConfig(label="身長（cm）", ymin=160, ymax=190, major_step=2, invert=False),
        right_axis=AxisConfig(label="体重（kg）", ymin=45, ymax=75, major_step=2, invert=False),
        series=[
            SeriesSpec(col="height_cm", label="身長（cm）", color_index=1, axis="left", linewidth=2.4),
            SeriesSpec(col="weight_kg", label="体重（kg）", color_index=2, axis="right", linewidth=2.4),
        ],
        roadmap=[
            RoadmapSpec(col="height_cm", axis="left"),
            RoadmapSpec(col="weight_kg", axis="right"),
        ],
    ),

    # 50m（早いほど上：9.0 -> 5.0、補助0.25）
    "run_50m": ChartSpec(
        title="走力推移（50m）",
        left_axis=AxisConfig(label="タイム（秒）", ymin=9.0, ymax=5.0, major_step=0.25, invert=True),
        right_axis=None,
        series=[
            SeriesSpec(col="run_50m_sec", label="50m（秒）", color_index=3, axis="left", linewidth=2.4),
        ],
        roadmap=[
            RoadmapSpec(col="run_50m_sec", axis="left"),
        ],
    ),

    # 1500m（5:00 -> 4:00、補助10sec、早いほど上）
    "run_1500m": ChartSpec(
        title="走力推移（1500m）",
        left_axis=AxisConfig(label="タイム（分:秒）", ymin=300, ymax=240, major_step=10, invert=True, formatter="sec_to_mmss"),
        right_axis=None,
        series=[
            SeriesSpec(col="run_1500m_sec", label="1500m", color_index=4, axis="left", linewidth=2.4),
        ],
        roadmap=[
            RoadmapSpec(col="run_1500m_sec", axis="left"),
        ],
    ),

    # 3000m（10:30 -> 9:30、補助10sec、早いほど上）
    "run_3000m": ChartSpec(
        title="走力推移（3000m）",
        left_axis=AxisConfig(label="タイム（分:秒）", ymin=630, ymax=570, major_step=10, invert=True, formatter="sec_to_mmss"),
        right_axis=None,
        series=[
            SeriesSpec(col="run_3000m_sec", label="3000m", color_index=5, axis="left", linewidth=2.4),
        ],
        roadmap=[
            RoadmapSpec(col="run_3000m_sec", axis="left"),
        ],
    ),

    # 学業（順位/偏差値）
    "academic_position": ChartSpec(
        title="学業（順位 / 偏差値）",
        left_axis=AxisConfig(label="学年順位", ymin=50, ymax=0, major_step=5, invert=True),
        right_axis=AxisConfig(label="参考偏差値", ymin=30, ymax=80, major_step=5, invert=False),
        series=[
            SeriesSpec(col="rank", label="学年順位", color_index=6, axis="left", linewidth=2.4),
            SeriesSpec(col="deviation", label="偏差値", color_index=2, axis="right", linewidth=2.4),
        ],
        roadmap=[
            RoadmapSpec(col="rank", axis="left"),
            RoadmapSpec(col="deviation", axis="right"),
        ],
    ),

    # 学業（評点/教科得点：国数英理社）
    "academic_scores_rating": ChartSpec(
        title="学業（評点 / 教科スコア）",
        left_axis=AxisConfig(label="評点", ymin=0, ymax=5, major_step=0.5, invert=False),
        right_axis=AxisConfig(label="教科得点", ymin=50, ymax=100, major_step=10, invert=False),
        series=[
            SeriesSpec(col="rating", label="評点", color_index=1, axis="left", linewidth=2.4),
            SeriesSpec(col="score_jp", label="国語", color_index=2, axis="right", linewidth=2.0),
            SeriesSpec(col="score_math", label="数学", color_index=3, axis="right", linewidth=2.0),
            SeriesSpec(col="score_en", label="英語", color_index=4, axis="right", linewidth=2.0),
            SeriesSpec(col="score_sci", label="理科", color_index=5, axis="right", linewidth=2.0),
            SeriesSpec(col="score_soc", label="社会", color_index=6, axis="right", linewidth=2.0),
        ],
        roadmap=[
            RoadmapSpec(col="rating", axis="left"),
            RoadmapSpec(col="score_jp", axis="right"),
            RoadmapSpec(col="score_math", axis="right"),
            RoadmapSpec(col="score_en", axis="right"),
            RoadmapSpec(col="score_sci", axis="right"),
            RoadmapSpec(col="score_soc", axis="right"),
        ],
    ),
}
