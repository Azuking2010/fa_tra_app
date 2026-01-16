# modules/report/report_charts.py
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter

from .report_logic import ReportData


# --------- formatters ----------
def _fmt_mmss(x, _pos=None) -> str:
    # seconds -> mm:ss
    try:
        if x is None or (isinstance(x, float) and np.isnan(x)):
            return ""
        sec = int(round(float(x)))
        m = sec // 60
        s = sec % 60
        return f"{m}:{s:02d}"
    except Exception:
        return ""


def _as_series(df: pd.DataFrame, col: str) -> pd.Series:
    if df is None or df.empty or col not in df.columns:
        return pd.Series(dtype=float)
    return pd.to_numeric(df[col], errors="coerce")


def _roadmap_band_for_metric(report: ReportData, metric_prefix: str) -> Optional[pd.DataFrame]:
    """
    metric_prefix 例:
      - "height_cm"
      - "weight_kg"
      - "bmi"
      - "run_100m_sec"
      - "run_1500m_sec"
      - "run_3000m_sec"
      - "rank"
      - "deviation"
      - "rating"
      - "score_jp" etc.

    戻り:
      columns: ["ym","low","mid","high"]
    """
    if report is None or not report.months:
        return None

    rows = []
    for ym in report.months:
        r = report.roadmap_for_month.get(ym, {}) or {}
        low = r.get(f"{metric_prefix}_low", np.nan)
        mid = r.get(f"{metric_prefix}_mid", np.nan)
        high = r.get(f"{metric_prefix}_high", np.nan)
        rows.append({"ym": ym, "low": low, "mid": mid, "high": high})

    df = pd.DataFrame(rows)
    # numeric 化（None/""はNaNへ）
    for c in ["low", "mid", "high"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


def _align_month_band_to_dates(
    dates: pd.Series,
    band_df: Optional[pd.DataFrame],
) -> Optional[pd.DataFrame]:
    """
    portfolio の各日付に対応する ym の band 値を割り当てる。
    """
    if band_df is None or band_df.empty or dates is None or dates.empty:
        return None

    yms = dates.apply(lambda d: f"{d.year:04d}-{d.month:02d}" if pd.notna(d) else "")
    mapping = band_df.set_index("ym")[["low", "mid", "high"]].to_dict(orient="index")

    low = []
    mid = []
    high = []
    for ym in yms:
        rec = mapping.get(ym, None)
        if rec is None:
            low.append(np.nan)
            mid.append(np.nan)
            high.append(np.nan)
        else:
            low.append(rec.get("low", np.nan))
            mid.append(rec.get("mid", np.nan))
            high.append(rec.get("high", np.nan))

    return pd.DataFrame({"low": low, "mid": mid, "high": high})


# --------- charts ----------
def fig_physical_height_weight_bmi(report: ReportData, show_roadmap: bool = True):
    """
    P2: 身長/体重/BMI（左=身長、右=体重&BMI）
    """
    df = report.portfolio
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    dates = df.get("_dt", pd.Series(dtype="datetime64[ns]"))
    height = _as_series(df, "height_cm")
    weight = _as_series(df, "weight_kg")

    # BMI は portfolio に列が無い可能性がある → 計算で対応（壊さない）
    bmi = pd.Series(np.nan, index=df.index)
    ok = height.notna() & weight.notna() & (height > 0)
    bmi.loc[ok] = weight.loc[ok] / ((height.loc[ok] / 100.0) ** 2)

    ax1.plot(dates, height, marker="o", linewidth=1, label="Height (cm)")
    ax2.plot(dates, weight, marker="o", linewidth=1, label="Weight (kg)")
    ax2.plot(dates, bmi, marker="o", linewidth=1, label="BMI")

    ax1.set_title("Physical: Height / Weight / BMI")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Height (cm)")
    ax2.set_ylabel("Weight (kg) / BMI")

    if show_roadmap:
        # height band on ax1
        band_h = _roadmap_band_for_metric(report, "height_cm")
        band_h2 = _align_month_band_to_dates(dates, band_h)
        if band_h2 is not None:
            ax1.fill_between(dates, band_h2["low"], band_h2["high"], alpha=0.15, label="Height target band")
            ax1.plot(dates, band_h2["mid"], linewidth=1, alpha=0.6, label="Height mid")

        # weight/bmi band on ax2
        band_w = _roadmap_band_for_metric(report, "weight_kg")
        band_w2 = _align_month_band_to_dates(dates, band_w)
        if band_w2 is not None:
            ax2.fill_between(dates, band_w2["low"], band_w2["high"], alpha=0.10, label="Weight target band")
            ax2.plot(dates, band_w2["mid"], linewidth=1, alpha=0.6, label="Weight mid")

        band_b = _roadmap_band_for_metric(report, "bmi")
        band_b2 = _align_month_band_to_dates(dates, band_b)
        if band_b2 is not None:
            ax2.fill_between(dates, band_b2["low"], band_b2["high"], alpha=0.08, label="BMI target band")
            ax2.plot(dates, band_b2["mid"], linewidth=1, alpha=0.6, label="BMI mid")

    # legends: combine
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="best")

    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def fig_run_metric(report: ReportData, metric: str, title: str, show_roadmap: bool = True, mmss: bool = False):
    """
    P2: 走力（50m / 1500 / 3000）
    """
    df = report.portfolio
    fig, ax = plt.subplots()

    dates = df.get("_dt", pd.Series(dtype="datetime64[ns]"))
    y = _as_series(df, metric)

    ax.plot(dates, y, marker="o", linewidth=1, label=metric)

    if show_roadmap:
        band = _roadmap_band_for_metric(report, metric)
        band2 = _align_month_band_to_dates(dates, band)
        if band2 is not None:
            ax.fill_between(dates, band2["low"], band2["high"], alpha=0.15, label="Target band")
            ax.plot(dates, band2["mid"], linewidth=1, alpha=0.6, label="Target mid")

    ax.set_title(title)
    ax.set_xlabel("Date")
    ax.set_ylabel("Seconds")

    if mmss:
        ax.yaxis.set_major_formatter(FuncFormatter(_fmt_mmss))
        ax.set_ylabel("Time (mm:ss)")

    ax.legend(loc="best")
    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def fig_academic_position(report: ReportData, show_roadmap: bool = True):
    """
    P3-上: 偏差値（左） & 順位（右・反転）
    """
    df = report.portfolio
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    dates = df.get("_dt", pd.Series(dtype="datetime64[ns]"))
    dev = _as_series(df, "deviation")
    rank = _as_series(df, "rank")

    ax1.plot(dates, dev, marker="o", linewidth=1, label="Deviation")
    ax2.plot(dates, rank, marker="o", linewidth=1, label="Rank")

    ax1.set_title("Academic: Deviation & Rank")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Deviation")
    ax2.set_ylabel("Rank (smaller is better)")
    ax2.invert_yaxis()  # これが効く：上がるほど良い見え方にする

    if show_roadmap:
        band_dev = _roadmap_band_for_metric(report, "deviation")
        band_dev2 = _align_month_band_to_dates(dates, band_dev)
        if band_dev2 is not None:
            ax1.fill_between(dates, band_dev2["low"], band_dev2["high"], alpha=0.12, label="Deviation band")
            ax1.plot(dates, band_dev2["mid"], linewidth=1, alpha=0.6, label="Deviation mid")

        band_rank = _roadmap_band_for_metric(report, "rank")
        band_rank2 = _align_month_band_to_dates(dates, band_rank)
        if band_rank2 is not None:
            ax2.fill_between(dates, band_rank2["low"], band_rank2["high"], alpha=0.08, label="Rank band")
            ax2.plot(dates, band_rank2["mid"], linewidth=1, alpha=0.6, label="Rank mid")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="best")

    fig.autofmt_xdate()
    fig.tight_layout()
    return fig


def fig_academic_scores_rating(report: ReportData, show_roadmap: bool = True):
    """
    P3-下: 評点（左） & 5教科（右）
    5教科は portfolio では列ごとに実績がある想定（score_*）
    """
    df = report.portfolio
    fig, ax1 = plt.subplots()
    ax2 = ax1.twinx()

    dates = df.get("_dt", pd.Series(dtype="datetime64[ns]"))
    rating = _as_series(df, "rating")

    # 5教科
    scores = {
        "JP": _as_series(df, "score_jp"),
        "Math": _as_series(df, "score_math"),
        "EN": _as_series(df, "score_en"),
        "Sci": _as_series(df, "score_sci"),
        "Soc": _as_series(df, "score_soc"),
    }

    ax1.plot(dates, rating, marker="o", linewidth=1, label="Rating")

    for name, s in scores.items():
        ax2.plot(dates, s, marker="o", linewidth=1, label=f"Score {name}")

    ax1.set_title("Academic: Rating & Subject Scores")
    ax1.set_xlabel("Date")
    ax1.set_ylabel("Rating")
    ax2.set_ylabel("Score (0-100)")

    if show_roadmap:
        band_rating = _roadmap_band_for_metric(report, "rating")
        band_rating2 = _align_month_band_to_dates(dates, band_rating)
        if band_rating2 is not None:
            ax1.fill_between(dates, band_rating2["low"], band_rating2["high"], alpha=0.10, label="Rating band")
            ax1.plot(dates, band_rating2["mid"], linewidth=1, alpha=0.6, label="Rating mid")

        # 5教科の帯：同一目標でもOKなので「JP」を代表にする（矛盾しない・見やすい）
        band_score = _roadmap_band_for_metric(report, "score_jp")
        band_score2 = _align_month_band_to_dates(dates, band_score)
        if band_score2 is not None:
            ax2.fill_between(dates, band_score2["low"], band_score2["high"], alpha=0.06, label="Score band")
            ax2.plot(dates, band_score2["mid"], linewidth=1, alpha=0.5, label="Score mid")

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="best")

    fig.autofmt_xdate()
    fig.tight_layout()
    return fig
