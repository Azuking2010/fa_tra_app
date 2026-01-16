# modules/roadmap/roadmap_logic.py
from __future__ import annotations

from typing import Optional
import pandas as pd
import re


def norm_ym(s: str) -> str:
    s = "" if s is None else str(s).strip()
    if not s:
        return ""
    s = s.replace("/", "-").replace(".", "-")
    m = re.match(r"^(\d{4})-(\d{1,2})$", s)
    if m:
        return f"{int(m.group(1)):04d}-{int(m.group(2)):02d}"
    m2 = re.match(r"^(\d{4})-(\d{2}).*$", s)
    if m2:
        return f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}"
    return s


def pick_active_rows(df: pd.DataFrame, ym: str) -> pd.DataFrame:
    """
    ym(YYYY-MM) が start_ym〜end_ym に入っている行を抽出
    """
    if df is None or df.empty:
        return df

    target = norm_ym(ym)
    if not target:
        return df.iloc[0:0].copy()

    # 文字列比較でOKなように必ず YYYY-MM に正規化済み前提
    start = df["start_ym"].astype(str)
    end = df["end_ym"].astype(str)

    mask = (start <= target) & (end >= target)
    return df.loc[mask].copy()


def pick_latest_row(df: pd.DataFrame) -> Optional[pd.Series]:
    """
    複数ヒットしたら「start_ym が一番新しい」を採用
    """
    if df is None or df.empty:
        return None
    tmp = df.copy()
    tmp["_k"] = tmp["start_ym"].astype(str)
    tmp = tmp.sort_values(by=["_k"], ascending=True)
    return tmp.iloc[-1]
