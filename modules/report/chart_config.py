# modules/report/chart_config.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple, Dict, List


# -----------------------------
# Color utilities
# -----------------------------
def hex_to_rgb01(hex_color: str) -> Tuple[float, float, float]:
    h = hex_color.lstrip("#")
    r = int(h[0:2], 16) / 255.0
    g = int(h[2:4], 16) / 255.0
    b = int(h[4:6], 16) / 255.0
    return (r, g, b)


def clamp01(x: float) -> float:
    return max(0.0, min(1.0, x))


def lighten(rgb: Tuple[float, float, float], amount: float = 0.18) -> Tuple[float, float, float]:
    # amount: 0..1
    r, g, b = rgb
    return (clamp01(r + (1 - r) * amount), clamp01(g + (1 - g) * amount), clamp01(b + (1 - b) * amount))


def darken(rgb: Tuple[float, float, float], amount: float = 0.18) -> Tuple[float, float, float]:
    r, g, b = rgb
    return (clamp01(r * (1 - amount)), clamp01(g * (1 - amount)), clamp01(b * (1 - amount)))


# -----------------------------
# Palette (6 colors)
# ※「提案したカラーでOK」とのことなので、安定して見やすいTableau系を採用
# -----------------------------
PALETTE_HEX: List[str] = [
    "#1f77b4",  # 1: blue
    "#ff7f0e",  # 2: orange
    "#2ca02c",  # 3: green
    "#d62728",  # 4: red
    "#9467bd",  # 5: purple
    "#8c564b",  # 6: brown
]

PALETTE_RGB01: List[Tuple[float, float, float]] = [hex_to_rgb01(h) for h in PALETTE_HEX]


@dataclass(frozen=True)
class AxisSpec:
    label: str
    vmin: float
    vmax: float
    major_step: float
    minor_step: Optional[float] = None
    invert: bool = False
    value_format: str = "plain"  # plain | sec_float | mmss | int


@dataclass(frozen=True)
class RoadmapSpec:
    enabled: bool = True
    # low/mid/high are drawn as dashed thin lines
    linestyle: str = (0, (3, 3))  # dashed
    linewidth: float = 1.1
    alpha: float = 0.55


@dataclass(frozen=True)
class LineStyle:
    color: Tuple[float, float, float]
    linewidth: float = 2.4
    marker: str = "o"
    markersize: float = 5.0


@dataclass(frozen=True)
class ChartSpec:
    title: str
    date_col: str

    # left axis
    left_axis: AxisSpec
    left_cols: Tuple[str, ...]
    left_labels: Tuple[str, ...]

    # right axis (optional)
    right_axis: Optional[AxisSpec] = None
    right_cols: Tuple[str, ...] = ()
    right_labels: Tuple[str, ...] = ()

    # styling
    palette_index_left: Tuple[int, ...] = (0,)  # indexes into PALETTE_RGB01
    palette_index_right: Tuple[int, ...] = (1,)
    roadmap: Optional[RoadmapSpec] = None

    # roadmap columns mapping (low/mid/high)
    roadmap_cols: Optional[Dict[str, Tuple[str, str, str]]] = None
    # roadmap is drawn on left axis by default (same scale)


# -----------------------------
# Fixed ranges (あなたがFIXした仕様)
# -----------------------------
CHART_SPECS: Dict[str, ChartSpec] = {
    # 身長/体重（BMIは当面無し）
    "height_weight": ChartSpec(
        title="フィジカル推移（身長・体重）",
        date_col="date",
        left_axis=AxisSpec(label="身長 (cm)", vmin=160.0, vmax=190.0, major_step=2.0, minor_step=2.0, invert=False, value_format="plain"),
        left_cols=("height_cm",),
        left_labels=("身長 (cm)",),
        right_axis=AxisSpec(label="体重 (kg)", vmin=45.0, vmax=75.0, major_step=2.0, minor_step=2.0, invert=False, value_format="plain"),
        right_cols=("weight_kg",),
        right_labels=("体重 (kg)",),
        palette_index_left=(0,),
        palette_index_right=(1,),
        roadmap=RoadmapSpec(enabled=True),
        roadmap_cols={
            "height_cm": ("height_cm_low", "height_cm_mid", "height_cm_high"),
            "weight_kg": ("weight_kg_low", "weight_kg_mid", "weight_kg_high"),
        },
    ),

    # 50m（速いほど上 → invert=True, 範囲は 9.0~5.0）
    "run_50m": ChartSpec(
        title="Run: 50m",
        date_col="date",
        left_axis=AxisSpec(label="タイム (秒)", vmin=9.0, vmax=5.0, major_step=0.5, minor_step=0.25, invert=True, value_format="sec_float"),
        left_cols=("run_100m_sec",),  # 既存列名を流用（あなたの現行仕様）
        left_labels=("50m",),
        palette_index_left=(0,),
        roadmap=RoadmapSpec(enabled=True),
        roadmap_cols={
            "run_100m_sec": ("run_100m_sec_low", "run_100m_sec_mid", "run_100m_sec_high"),
        },
    ),

    # 1500m（5:00~4:00, 補助10sec）
    "run_1500m": ChartSpec(
        title="Run: 1500m",
        date_col="date",
        left_axis=AxisSpec(label="タイム (分:秒)", vmin=300.0, vmax=240.0, major_step=10.0, minor_step=10.0, invert=True, value_format="mmss"),
        left_cols=("run_1500m_sec",),
        left_labels=("1500m",),
        palette_index_left=(0,),
        roadmap=RoadmapSpec(enabled=True),
        roadmap_cols={
            "run_1500m_sec": ("run_1500m_sec_low", "run_1500m_sec_mid", "run_1500m_sec_high"),
        },
    ),

    # 3000m（10:30~9:30, 補助10sec）
    "run_3000m": ChartSpec(
        title="Run: 3000m",
        date_col="date",
        left_axis=AxisSpec(label="タイム (分:秒)", vmin=630.0, vmax=570.0, major_step=10.0, minor_step=10.0, invert=True, value_format="mmss"),
        left_cols=("run_3000m_sec",),
        left_labels=("3000m",),
        palette_index_left=(0,),
        roadmap=RoadmapSpec(enabled=True),
        roadmap_cols={
            "run_3000m_sec": ("run_3000m_sec_low", "run_3000m_sec_mid", "run_3000m_sec_high"),
        },
    ),

    # 学年順位 / 偏差値（左：50~0, 右：30~80）
    "academic_rank_dev": ChartSpec(
        title="学業（順位/偏差値）",
        date_col="date",
        left_axis=AxisSpec(label="学年順位", vmin=50.0, vmax=0.0, major_step=5.0, minor_step=5.0, invert=True, value_format="int"),
        left_cols=("rank",),
        left_labels=("学年順位",),
        right_axis=AxisSpec(label="参考偏差値", vmin=30.0, vmax=80.0, major_step=5.0, minor_step=5.0, invert=False, value_format="plain"),
        right_cols=("deviation",),
        right_labels=("偏差値",),
        palette_index_left=(2,),
        palette_index_right=(4,),
        roadmap=RoadmapSpec(enabled=True),
        roadmap_cols={
            "rank": ("rank_low", "rank_mid", "rank_high"),
            "deviation": ("deviation_low", "deviation_mid", "deviation_high"),
        },
    ),

    # 評点 / 教科スコア（右は5本以上になる想定）
    "academic_scores": ChartSpec(
        title="学業（評点/教科スコア）",
        date_col="date",
        left_axis=AxisSpec(label="評点", vmin=0.0, vmax=5.0, major_step=0.5, minor_step=0.5, invert=False, value_format="plain"),
        left_cols=("rating",),
        left_labels=("評点",),
        right_axis=AxisSpec(label="教科スコア", vmin=50.0, vmax=100.0, major_step=10.0, minor_step=10.0, invert=False, value_format="int"),
        right_cols=("score_jp", "score_math", "score_en", "score_sci", "score_soc"),
        right_labels=("国語", "数学", "英語", "理科", "社会"),
        palette_index_left=(3,),
        palette_index_right=(0, 1, 2, 4, 5),
        roadmap=RoadmapSpec(enabled=True),
        roadmap_cols={
            "rating": ("rating_low", "rating_mid", "rating_high"),
            "score_jp": ("score_jp_low", "score_jp_mid", "score_jp_high"),
            "score_math": ("score_math_low", "score_math_mid", "score_math_high"),
            "score_en": ("score_en_low", "score_en_mid", "score_en_high"),
            "score_sci": ("score_sci_low", "score_sci_mid", "score_sci_high"),
            "score_soc": ("score_soc_low", "score_soc_mid", "score_soc_high"),
        },
    ),
}
