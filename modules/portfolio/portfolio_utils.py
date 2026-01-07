# modules/portfolio_utils.py
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd


# ★ 固定列（1行目ヘッダーとして横貼りする前提）
PORTFOLIO_COLUMNS: List[str] = [
    "date",
    "height_cm",
    "weight_kg",
    "bmi",  # Sheets数式で自動計算
    "run_100m_sec",
    "run_1500m_sec",
    "run_3000m_sec",
    "track_meet",          # 陸上大会名（run系の後ろ）
    "rank",
    "deviation",
    "score_jp",
    "score_math",
    "score_en",
    "score_sci",
    "score_soc",
    "rating",
    "tcenter",
    "soccer_tournament",   # サッカー大会名（match_resultの手前）
    "match_result",
    "video_url",
    "video_note",
    "note",
]


def now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def build_bmi_formula(row_index_1based: int) -> str:
    """
    bmi 列(D)に入れる想定。
    B=height_cm, C=weight_kg
    """
    r = row_index_1based
    # BMI = weight / (height_m^2)
    # height_cm -> m: /100
    return f'=IF(OR(B{r}="",C{r}=""),"",ROUND(C{r}/((B{r}/100)^2),1))'


def sanitize_float(v: Optional[str]) -> Optional[float]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return float(s)
    except Exception:
        return None


def sanitize_int(v: Optional[str]) -> Optional[int]:
    if v is None:
        return None
    s = str(v).strip()
    if s == "":
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def df_from_sheet_values(values: List[List[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

    header = values[0]
    data = values[1:] if len(values) >= 2 else []

    df = pd.DataFrame(data, columns=header)

    # 欠けてる列は追加（将来拡張に備える）
    for c in PORTFOLIO_COLUMNS:
        if c not in df.columns:
            df[c] = ""

    # 余分な列があってもOK（必要列だけ使う）
    df = df[PORTFOLIO_COLUMNS]

    return df


def latest_non_empty_by_column(df: pd.DataFrame) -> Dict[str, str]:
    """
    「最新行」ではなく、「各列ごとに最新の値」を返す。
    ＝T.Aが言ってた “最新の値を採用” ルール用。
    """
    if df is None or df.empty:
        return {c: "" for c in PORTFOLIO_COLUMNS}

    # date昇順、同日複数は行順で後ろが新しい想定
    df2 = df.copy()
    df2["__date_sort__"] = pd.to_datetime(df2["date"], errors="coerce")
    df2 = df2.sort_values(["__date_sort__"], ascending=True)

    out: Dict[str, str] = {c: "" for c in PORTFOLIO_COLUMNS}
    for _, row in df2.iterrows():
        for c in PORTFOLIO_COLUMNS:
            if c == "bmi":
                # BMIは表示用。入力のデフォルトには使わない（数式で出る想定）
                continue
            val = "" if pd.isna(row.get(c)) else str(row.get(c)).strip()
            if val != "":
                out[c] = val

    return out


def ensure_header_exact(ws) -> None:
    """
    1行目が空、または列が違う場合にヘッダーを強制設定。
    """
    values = ws.get_all_values()
    if not values:
        ws.update("A1", [PORTFOLIO_COLUMNS])
        return

    header = values[0]
    if header != PORTFOLIO_COLUMNS:
        # 既存がズレてたら上書きで揃える（列決め打ちが前提）
        ws.update("A1", [PORTFOLIO_COLUMNS])
