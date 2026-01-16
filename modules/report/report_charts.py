# modules/report/report_charts.py
from __future__ import annotations

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
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
def _setup_ax(ax, title: str, ylabel_left: str | None = None, ylabel_right: str | None = None):
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    if ylabel_left:
        ax.set_ylabel(ylabel_left)
    if ylabel_right:
        ax.right_ax.set_ylabel(ylabel_right)


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2  # util 用

    ax1.plot(df["date"], df["height_cm"], label="Height (cm)", color="tab:blue")
    ax2.plot(df["date"], df["weight_kg"], label="Weight (kg)", color="tab:orange")
    if "bmi" in df.columns:
        ax2.plot(df["date"], df["bmi"], label="BMI", color="tab:green", linestyle="--")

    _setup_ax(ax1, "Physical Growth", "Height (cm)", "Weight / BMI")

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

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["date"], df[metric], marker="o")

    ax.set_title(title)
    ax.set_ylabel("Time (sec)")
    ax.grid(True, axis="y", alpha=0.3)

    return fig


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rank"], label="Rank", color="tab:red")
    ax2.plot(df["date"], df["deviation"], label="Deviation", color="tab:blue")

    _setup_ax(ax1, "Academic Position", "Rank", "Deviation")

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    return fig


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rating"], label="Rating", color="black", linewidth=2)

    for col in ["score_jp", "score_math", "score_en", "score_sci", "score_soc"]:
        if col in df.columns:
            ax2.plot(df["date"], df[col], label=col)

    _setup_ax(ax1, "Academic Scores", "Rating", "Scores")

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)

    return fig
