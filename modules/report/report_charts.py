# modules/report/report_charts.py
from __future__ import annotations

from datetime import datetime

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False


def _require_mpl():
    if not HAS_MPL:
        raise ModuleNotFoundError(
            "matplotlib is required for report charts, but it is not installed."
        )


# =========================================================
# 共通ユーティリティ
# =========================================================
def _date_range_str(df) -> str:
    if df.empty:
        return ""
    start = df["date"].min()
    end = df["date"].max()
    return f"{start} 〜 {end}"


def _annotate_latest(ax, x, y, fmt=str):
    """最新値を右端に注釈"""
    if len(x) == 0:
        return
    ax.annotate(
        fmt(y.iloc[-1]),
        (x.iloc[-1], y.iloc[-1]),
        xytext=(5, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        color="black",
    )


def _sec_to_mmss(sec: float) -> str:
    if sec is None:
        return ""
    sec = int(round(sec))
    m = sec // 60
    s = sec % 60
    return f"{m}:{s:02d}"


def _mmss_formatter(x, pos):
    return _sec_to_mmss(x)


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _date_range_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["height_cm"], label="身長 (cm)", color="tab:blue")
    ax2.plot(df["date"], df["weight_kg"], label="体重 (kg)", color="tab:orange")

    if "bmi" in df.columns:
        ax2.plot(df["date"], df["bmi"], label="BMI", color="tab:green", linestyle="--")

    ax1.set_title(f"フィジカル成長推移\n{period}")
    ax1.set_ylabel("身長 (cm)")
    ax2.set_ylabel("体重 / BMI")
    ax1.grid(True, axis="y", alpha=0.3)

    _annotate_latest(ax1, df["date"], df["height_cm"], lambda v: f"{v:.1f}cm")
    _annotate_latest(ax2, df["date"], df["weight_kg"], lambda v: f"{v:.1f}kg")

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    return fig


# =========================================================
# P2: 走力（50m / 1500m / 3000m）
# =========================================================
def fig_run_metric(
    report,
    metric: str,
    title: str,
    show_roadmap: bool = True,
    mmss: bool = False,
):
    _require_mpl()

    df = report.portfolio
    period = _date_range_str(df)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["date"], df[metric], marker="o")

    ax.set_title(f"{title}\n{period}")
    ax.grid(True, axis="y", alpha=0.3)

    if mmss:
        ax.set_ylabel("タイム (分:秒)")
        ax.yaxis.set_major_formatter(FuncFormatter(_mmss_formatter))
        _annotate_latest(ax, df["date"], df[metric], _sec_to_mmss)
    else:
        ax.set_ylabel("タイム (秒)")
        _annotate_latest(ax, df["date"], df[metric], lambda v: f"{v:.2f}s")

    return fig


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _date_range_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rank"], label="学年順位", color="tab:red")
    ax2.plot(df["date"], df["deviation"], label="偏差値", color="tab:blue")

    ax1.set_title(f"学業成績（順位・偏差値）\n{period}")
    ax1.set_ylabel("順位")
    ax2.set_ylabel("偏差値")
    ax1.grid(True, axis="y", alpha=0.3)

    _annotate_latest(ax1, df["date"], df["rank"], lambda v: f"{int(v)}位")
    _annotate_latest(ax2, df["date"], df["deviation"], lambda v: f"{v:.1f}")

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    return fig


# =========================================================
# P3: 学業（評点・各教科）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _date_range_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rating"], label="評点", color="black", linewidth=2)

    for col, label in [
        ("score_jp", "国語"),
        ("score_math", "数学"),
        ("score_en", "英語"),
        ("score_sci", "理科"),
        ("score_soc", "社会"),
    ]:
        if col in df.columns:
            ax2.plot(df["date"], df[col], label=label)

    ax1.set_title(f"学業成績（評点・各教科）\n{period}")
    ax1.set_ylabel("評点")
    ax2.set_ylabel("教科別スコア")
    ax1.grid(True, axis="y", alpha=0.3)

    _annotate_latest(ax1, df["date"], df["rating"], lambda v: f"{v:.1f}")

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)

    return fig
