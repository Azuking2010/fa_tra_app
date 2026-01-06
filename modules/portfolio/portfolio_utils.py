from __future__ import annotations

from datetime import datetime, timedelta
import pandas as pd


def _to_date(s: str):
    try:
        return datetime.strptime(str(s), "%Y-%m-%d").date()
    except Exception:
        return None


def filter_by_days(df: pd.DataFrame, days: int) -> pd.DataFrame:
    """直近N日"""
    if df.empty:
        return df.copy()

    df2 = df.copy()
    df2["__date"] = df2["date"].apply(_to_date)
    df2 = df2[df2["__date"].notna()].copy()

    cutoff = (datetime.now().date() - timedelta(days=days))
    df2 = df2[df2["__date"] >= cutoff]
    return df2.drop(columns=["__date"], errors="ignore")


def latest_body_series(df: pd.DataFrame, metric: str) -> pd.DataFrame:
    """
    body系の推移（例: height/weight/bmi）
    """
    if df.empty:
        return pd.DataFrame(columns=["date", "value_num"])

    d = df[(df["category"] == "body") & (df["metric"] == metric)].copy()
    if d.empty:
        return pd.DataFrame(columns=["date", "value_num"])

    d = d[["date", "value_num"]].copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"]).sort_values("date")
    return d
