# modules/report/chart_config.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Dict, Any, List, Tuple

# =========================================
# Color helpers
# =========================================
def _to_rgb01(c):
    """Accept 'tab:blue' etc is handled by matplotlib, so here we only handle rgb tuples."""
    return c

def adjust_brightness_rgb(rgb: Tuple[float, float, float], mode: str, factor: float = 0.75):
    """
    mode:
      - "dark":  rgb * factor
      - "light": 1 - (1-rgb)*factor
    """
    r, g, b = rgb
    if mode == "dark":
        return (max(0.0, r * factor), max(0.0, g * factor), max(0.0, b * factor))
    if mode == "light":
        return (min(1.0, 1 - (1 - r) * factor), min(1.0, 1 - (1 - g) * factor), min(1.0, 1 - (1 - b) * factor))
    return rgb


# =========================================
# Axis / ticks specs
# =========================================
@dataclass(frozen=True)
class AxisSpec:
    ymin: float
    ymax: float
    major: float
    minor: Optional[float] = None
    invert: bool = False  # True = smaller values appear higher (y-axis reversed)


@dataclass(frozen=True)
class SeriesSpec:
    key: str               # dataframe column name
    label: str            # display label
    color: Any            # matplotlib color (e.g. 'tab:blue' or (r,g,b))
    linewidth: float = 2.0
    marker: str = "o"


@dataclass(frozen=True)
class ChartSpec:
    chart_id: str
    title: str
    x: str
    left_axis: AxisSpec
    right_axis: Optional[AxisSpec] = None
    left_series: Optional[List[SeriesSpec]] = None
    right_series: Optional[List[SeriesSpec]] = None
    # value formatting
    y_format: Optional[str] = None  # "mmss" etc (for left axis only; for run charts)
    # roadmap overlay settings
    roadmap_key_prefix: Optional[str] = None  # e.g. "height_cm" -> roadmap columns derived elsewhere


# =========================================
# Base palette (1〜6)
# =========================================
PALETTE = {
    1: "tab:blue",
    2: "tab:orange",
    3: "tab:green",
    4: "tab:red",
    5: "tab:purple",
    6: "tab:brown",
}

# If you want strict RGB later, replace with tuples:
# e.g. PALETTE = {1:(0.12,0.47,0.71), ...}


# =========================================
# Chart specs
# =========================================
CHARTS: Dict[str, ChartSpec] = {
    "physical_height_weight": ChartSpec(
        chart_id="physical_height_weight",
        title="フィジカル推移（身長・体重）",
        x="date",
        left_axis=AxisSpec(ymin=160, ymax=190, major=2, minor=2, invert=False),
        right_axis=AxisSpec(ymin=45, ymax=75, major=2, minor=2, invert=False),
        left_series=[
            SeriesSpec(key="height_cm", label="身長（cm）", color=PALETTE[1]),
        ],
        right_series=[
            SeriesSpec(key="weight_kg", label="体重（kg）", color=PALETTE[2]),
        ],
    ),

    "run_50m": ChartSpec(
        chart_id="run_50m",
        title="走力：50m",
        x="date",
        left_axis=AxisSpec(ymin=9.0, ymax=5.0, major=0.5, minor=0.25, invert=True),
        left_series=[SeriesSpec(key="run_50m_sec", label="50m（秒）", color=PALETTE[1])],
        y_format=None,
    ),

    "run_1500m": ChartSpec(
        chart_id="run_1500m",
        title="走力：1500m",
        x="date",
        left_axis=AxisSpec(ymin=5*60, ymax=4*60, major=10, minor=10, invert=True),
        left_series=[SeriesSpec(key="run_1500m_sec", label="1500m", color=PALETTE[1])],
        y_format="mmss",
    ),

    "run_3000m": ChartSpec(
        chart_id="run_3000m",
        title="走力：3000m",
        x="date",
        left_axis=AxisSpec(ymin=10*60+30, ymax=9*60+30, major=10, minor=10, invert=True),
        left_series=[SeriesSpec(key="run_3000m_sec", label="3000m", color=PALETTE[1])],
        y_format="mmss",
    ),

    "academic_rank_dev": ChartSpec(
        chart_id="academic_rank_dev",
        title="学業推移（順位・偏差値）",
        x="date",
        left_axis=AxisSpec(ymin=50, ymax=0, major=5, minor=5, invert=True),
        right_axis=AxisSpec(ymin=30, ymax=80, major=5, minor=5, invert=False),
        left_series=[SeriesSpec(key="rank", label="学年順位", color=PALETTE[4])],
        right_series=[SeriesSpec(key="deviation", label="偏差値", color=PALETTE[1])],
    ),

    "academic_rating_scores": ChartSpec(
        chart_id="academic_rating_scores",
        title="学業推移（評点・教科スコア）",
        x="date",
        left_axis=AxisSpec(ymin=0, ymax=5, major=0.5, minor=0.5, invert=False),
        right_axis=AxisSpec(ymin=50, ymax=100, major=10, minor=10, invert=False),
        left_series=[SeriesSpec(key="rating", label="評点", color="black", linewidth=2.5)],
        right_series=[
            SeriesSpec(key="score_jp", label="国語", color=PALETTE[1]),
            SeriesSpec(key="score_math", label="数学", color=PALETTE[2]),
            SeriesSpec(key="score_en", label="英語", color=PALETTE[3]),
            SeriesSpec(key="score_sci", label="理科", color=PALETTE[5]),
            SeriesSpec(key="score_soc", label="社会", color=PALETTE[6]),
        ],
    ),
}
