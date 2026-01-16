# modules/roadmap/roadmap_schema.py
from __future__ import annotations

from typing import List, Set


# ===== Roadmap schema (future targets) =====
ROADMAP_COLUMNS: List[str] = [
    "start_ym",
    "end_ym",
    "height_cm_low",
    "height_cm_mid",
    "height_cm_high",
    "weight_kg_low",
    "weight_kg_mid",
    "weight_kg_high",
    "bmi_low",
    "bmi_mid",
    "bmi_high",
    "run_100m_sec_low",
    "run_100m_sec_mid",
    "run_100m_sec_high",
    "run_1500m_sec_low",
    "run_1500m_sec_mid",
    "run_1500m_sec_high",
    "run_3000m_sec_low",
    "run_3000m_sec_mid",
    "run_3000m_sec_high",
    "rank_low",
    "rank_mid",
    "rank_high",
    "deviation_low",
    "deviation_mid",
    "deviation_high",
    "score_jp_low",
    "score_jp_mid",
    "score_jp_high",
    "score_math_low",
    "score_math_mid",
    "score_math_high",
    "score_en_low",
    "score_en_mid",
    "score_en_high",
    "score_sci_low",
    "score_sci_mid",
    "score_sci_high",
    "score_soc_low",
    "score_soc_mid",
    "score_soc_high",
    "rating_low",
    "rating_mid",
    "rating_high",
    "tcenter",
    "soccer_tournament",
    "match_result",
    "topic_text",
    "achieved",
    "note",
]

# 数値化して扱いたい列（*_low/_mid/_high は数値）
ROADMAP_NUMERIC_COLS: Set[str] = set()
for c in ROADMAP_COLUMNS:
    if c.endswith("_low") or c.endswith("_mid") or c.endswith("_high"):
        ROADMAP_NUMERIC_COLS.add(c)

# bool扱い（表示/フィルタで扱いやすくする）
ROADMAP_BOOL_COLS: Set[str] = {"tcenter"}

# achieved は TRUE/FALSE/空など運用が揺れやすいので、当面は文字列として扱う（必要なら後でbool化）
