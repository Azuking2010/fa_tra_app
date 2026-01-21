# modules/report/charts_definitions.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

# A series is: (column_name, label, style_kwargs)
SeriesDef = Tuple[str, str, Dict[str, Any]]


@dataclass(frozen=True)
class AxisSpec:
    label: str
    ymin: float
    ymax: float
    major_step: float
    invert: bool = False
    # formatter: "none" | "mmss"
    formatter: str = "none"


@dataclass(frozen=True)
class ChartSpec:
    key: str
    title: str
    left: AxisSpec
    right: Optional[AxisSpec]
    left_series: List[SeriesDef]
    right_series: List[SeriesDef]


# =========================
# Color palette (6 colors)
# =========================
# Matplotlib tab10 first 6 (stable and readable)
PALETTE = [
    "#1f77b4",  # 1
    "#ff7f0e",  # 2
    "#2ca02c",  # 3
    "#d62728",  # 4
    "#9467bd",  # 5
    "#8c564b",  # 6
]


def _roadmap_color(base_hex: str, mode: str) -> str:
    """
    mode: 'low' | 'mid' | 'high'
    We keep this simple and deterministic (no external deps).
    """
    base_hex = base_hex.lstrip("#")
    r = int(base_hex[0:2], 16)
    g = int(base_hex[2:4], 16)
    b = int(base_hex[4:6], 16)

    def clamp(x: int) -> int:
        return max(0, min(255, x))

    if mode == "low":
        # slightly darker
        r, g, b = clamp(int(r * 0.78)), clamp(int(g * 0.78)), clamp(int(b * 0.78))
    elif mode == "high":
        # slightly lighter
        r, g, b = clamp(int(r + (255 - r) * 0.35)), clamp(int(g + (255 - g) * 0.35)), clamp(int(b + (255 - b) * 0.35))
    else:
        # mid: base
        pass

    return f"#{r:02x}{g:02x}{b:02x}"


# =========================
# CHARTS definitions
# =========================
CHARTS: Dict[str, ChartSpec] = {}

# --- P2: 身長 / 体重（BMIは一旦無し）
CHARTS["height_weight"] = ChartSpec(
    key="height_weight",
    title="フィジカル推移（身長・体重）",
    left=AxisSpec(label="身長 (cm)", ymin=160, ymax=190, major_step=2, invert=False, formatter="none"),
    right=AxisSpec(label="体重 (kg)", ymin=45, ymax=75, major_step=2, invert=False, formatter="none"),
    left_series=[
        ("height_cm", "身長 (cm)", {"color": PALETTE[0], "linewidth": 2.2, "marker": "o"}),
    ],
    right_series=[
        ("weight_kg", "体重 (kg)", {"color": PALETTE[1], "linewidth": 2.2, "marker": "o"}),
    ],
)

# --- P2: 50m（速いほど上 → 軸反転）
CHARTS["run_50m"] = ChartSpec(
    key="run_50m",
    title="Run: 50m",
    left=AxisSpec(label="タイム (秒)", ymin=9.0, ymax=5.0, major_step=0.25, invert=True, formatter="none"),
    right=None,
    left_series=[
        ("run_50m_sec", "50m", {"color": PALETTE[0], "linewidth": 2.2, "marker": "o"}),
    ],
    right_series=[],
)

# --- P2: 1500m（5:00〜4:00、補助10sec、速いほど上 → 軸反転、mm:ss表示）
CHARTS["run_1500m"] = ChartSpec(
    key="run_1500m",
    title="Run: 1500m",
    left=AxisSpec(label="タイム (分:秒)", ymin=300, ymax=240, major_step=10, invert=True, formatter="mmss"),
    right=None,
    left_series=[
        ("run_1500m_sec", "1500m", {"color": PALETTE[0], "linewidth": 2.2, "marker": "o"}),
    ],
    right_series=[],
)

# --- P2: 3000m（10:30〜9:30、補助10sec、速いほど上 → 軸反転、mm:ss表示）
CHARTS["run_3000m"] = ChartSpec(
    key="run_3000m",
    title="Run: 3000m",
    left=AxisSpec(label="タイム (分:秒)", ymin=630, ymax=570, major_step=10, invert=True, formatter="mmss"),
    right=None,
    left_series=[
        ("run_3000m_sec", "3000m", {"color": PALETTE[0], "linewidth": 2.2, "marker": "o"}),
    ],
    right_series=[],
)

# --- P3: 学業（順位/偏差値）
CHARTS["academic_rank_dev"] = ChartSpec(
    key="academic_rank_dev",
    title="学業（順位/偏差値）",
    left=AxisSpec(label="学年順位", ymin=50, ymax=0, major_step=5, invert=True, formatter="none"),
    right=AxisSpec(label="参考偏差値", ymin=30, ymax=80, major_step=5, invert=False, formatter="none"),
    left_series=[
        ("rank_grade", "学年順位", {"color": PALETTE[0], "linewidth": 2.2, "marker": "o"}),
    ],
    right_series=[
        ("deviation", "参考偏差値", {"color": PALETTE[1], "linewidth": 2.2, "marker": "o"}),
    ],
)

# --- P3: 学業（評点/教科テスト）
CHARTS["academic_scores"] = ChartSpec(
    key="academic_scores",
    title="学業（評点/教科スコア）",
    left=AxisSpec(label="評点", ymin=0, ymax=5, major_step=0.5, invert=False, formatter="none"),
    right=AxisSpec(label="教科スコア", ymin=50, ymax=100, major_step=10, invert=False, formatter="none"),
    left_series=[
        ("rating", "評点", {"color": PALETTE[0], "linewidth": 2.2, "marker": "o"}),
    ],
    right_series=[
        ("score_jp", "国語", {"color": PALETTE[1], "linewidth": 2.0, "marker": "o"}),
        ("score_math", "数学", {"color": PALETTE[2], "linewidth": 2.0, "marker": "o"}),
        ("score_eng", "英語", {"color": PALETTE[3], "linewidth": 2.0, "marker": "o"}),
        ("score_sci", "理科", {"color": PALETTE[4], "linewidth": 2.0, "marker": "o"}),
        ("score_soc", "社会", {"color": PALETTE[5], "linewidth": 2.0, "marker": "o"}),
    ],
)


# ROADMAP style helpers (thin dotted, same-family colors)
ROADMAP_STYLE = {
    "linewidth": 1.2,
    "linestyle": (0, (2, 2)),  # thin dotted-like
    "alpha": 0.85,
}

def roadmap_styles_for_base(base_hex: str) -> Dict[str, Dict[str, Any]]:
    return {
        "low":  {"color": _roadmap_color(base_hex, "low"),  **ROADMAP_STYLE},
        "mid":  {"color": _roadmap_color(base_hex, "mid"),  **ROADMAP_STYLE},
        "high": {"color": _roadmap_color(base_hex, "high"), **ROADMAP_STYLE},
    }
