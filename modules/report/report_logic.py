# modules/report/report_logic.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import pandas as pd


def _to_datetime_safe(series: pd.Series) -> pd.Series:
    # portfolio の date は文字列想定。壊さない原則：失敗しても NaT で落とさない
    return pd.to_datetime(series, errors="coerce")


def _month_range_ym(start_date: pd.Timestamp, end_date: pd.Timestamp) -> List[str]:
    # start_date/end_date を含む月リスト（YYYY-MM）
    if pd.isna(start_date) or pd.isna(end_date):
        return []
    start = pd.Timestamp(year=start_date.year, month=start_date.month, day=1)
    end = pd.Timestamp(year=end_date.year, month=end_date.month, day=1)
    out = []
    cur = start
    while cur <= end:
        out.append(f"{cur.year:04d}-{cur.month:02d}")
        cur = cur + pd.offsets.MonthBegin(1)
    return out


def _parse_ym(ym: str) -> Optional[pd.Timestamp]:
    ym = (ym or "").strip()
    if not ym:
        return None
    try:
        return pd.to_datetime(ym + "-01", errors="coerce")
    except Exception:
        return None


def _ym_in_range(target_ym: str, start_ym: str, end_ym: str) -> bool:
    t = _parse_ym(target_ym)
    s = _parse_ym(start_ym)
    e = _parse_ym(end_ym)
    if t is None or s is None or e is None:
        return False
    return s <= t <= e


def _pick_roadmap_row_for_ym(roadmap_df: pd.DataFrame, ym: str) -> Optional[pd.Series]:
    if roadmap_df is None or roadmap_df.empty:
        return None
    # 条件に合う行を全部拾って「最初の行」を採用（運用上は重複しない前提）
    mask = roadmap_df.apply(
        lambda r: _ym_in_range(ym, str(r.get("start_ym", "")), str(r.get("end_ym", ""))),
        axis=1,
    )
    hit = roadmap_df[mask]
    if hit.empty:
        return None
    return hit.iloc[0]


@dataclass
class ReportData:
    meta: Dict[str, Any]
    portfolio: pd.DataFrame  # 期間フィルタ済み
    roadmap_for_month: Dict[str, Dict[str, Any]]  # ym -> {col: value}
    months: List[str]


def build_report_data(
    portfolio_df: pd.DataFrame,
    roadmap_df: pd.DataFrame,
    start_date: Any,
    end_date: Any,
) -> ReportData:
    """
    UI / PDF / JSON の共通“真実”を生成する。

    - portfolio_df: storage.load_all_portfolio() の戻り想定
    - roadmap_df: modules/roadmap/roadmap_storage.RoadmapSheetsStorage.load_all() の戻り想定
    - start_date/end_date: date_input の値（datetime.date など）
    """
    # --- portfolio 前処理 ---
    df = portfolio_df.copy() if portfolio_df is not None else pd.DataFrame()
    if df.empty:
        df = pd.DataFrame()

    if "date" in df.columns:
        df["_dt"] = _to_datetime_safe(df["date"])
    else:
        df["_dt"] = pd.NaT

    # start/end を Timestamp 化
    s = pd.to_datetime(start_date, errors="coerce")
    e = pd.to_datetime(end_date, errors="coerce")

    if pd.isna(s) or pd.isna(e):
        # 入力が壊れていても落とさない
        df_period = df[df["_dt"].notna()].copy()
    else:
        # end は 23:59:59 まで含めるイメージ
        e2 = e + pd.Timedelta(days=1) - pd.Timedelta(seconds=1)
        df_period = df[(df["_dt"] >= s) & (df["_dt"] <= e2)].copy()

    df_period = df_period.sort_values("_dt").reset_index(drop=True)

    # 期間の月リスト
    months = _month_range_ym(s, e) if (not pd.isna(s) and not pd.isna(e)) else []

    # ym -> roadmap row dict
    roadmap_for_month: Dict[str, Dict[str, Any]] = {}
    for ym in months:
        row = _pick_roadmap_row_for_ym(roadmap_df, ym)
        if row is None:
            roadmap_for_month[ym] = {}
        else:
            # Series -> dict（NaNも許容）
            roadmap_for_month[ym] = {k: row.get(k) for k in row.index}

    meta = {
        "start_date": str(start_date),
        "end_date": str(end_date),
        "months": months,
        "portfolio_rows": int(len(df_period)),
        "has_roadmap": bool(roadmap_df is not None and not roadmap_df.empty),
    }

    return ReportData(
        meta=meta,
        portfolio=df_period,
        roadmap_for_month=roadmap_for_month,
        months=months,
    )
