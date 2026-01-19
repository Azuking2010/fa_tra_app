# modules/report/report_charts.py
from __future__ import annotations

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
def _setup_ax(ax, title: str, ylabel_left: str | None = None, ylabel_right: str | None = None):
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    ax.set_xlabel("日付")
    if ylabel_left:
        ax.set_ylabel(ylabel_left)
    if ylabel_right:
        ax.right_ax.set_ylabel(ylabel_right)


def _sec_to_mmss(sec: float) -> str:
    if sec is None or sec <= 0:
        return ""
    m = int(sec) // 60
    s = int(sec) % 60
    return f"{m}:{s:02d}"


def _mmss_formatter():
    return FuncFormatter(lambda x, _: _sec_to_mmss(x))


def _period_str(df):
    if df.empty:
        return ""
    start = df["date"].iloc[0]
    end = df["date"].iloc[-1]
    return f"{start} 〜 {end}"


def _annotate_latest(ax, x, y, text: str):
    if y is None:
        return
    ax.annotate(
        text,
        xy=(x, y),
        xytext=(5, 5),
        textcoords="offset points",
        fontsize=10,
        fontweight="bold",
    )


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["height_cm"], label="身長（cm）", color="tab:blue", marker="o")
    ax2.plot(df["date"], df["weight_kg"], label="体重（kg）", color="tab:orange", marker="o")

    if "bmi" in df.columns:
        ax2.plot(df["date"], df["bmi"], label="BMI", color="tab:green", linestyle="--")

    _setup_ax(
        ax1,
        f"身体成長の推移（{period}）",
        ylabel_left="身長（cm）",
        ylabel_right="体重 / BMI",
    )

    _annotate_latest(ax1, df["date"].iloc[-1], df["height_cm"].iloc[-1], f"{df['height_cm'].iloc[-1]:.1f}cm")
    _annotate_latest(ax2, df["date"].iloc[-1], df["weight_kg"].iloc[-1], f"{df['weight_kg'].iloc[-1]:.1f}kg")

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
    period = _period_str(df)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["date"], df[metric], marker="o")

    ylabel = "タイム（秒）"
    if mmss:
        ax.yaxis.set_major_formatter(_mmss_formatter())
        ylabel = "タイム（mm:ss）"

    ax.set_title(f"{title}の推移（{period}）")
    ax.set_xlabel("日付")
    ax.set_ylabel(ylabel)
    ax.grid(True, axis="y", alpha=0.3)

    latest_y = df[metric].iloc[-1]
    label = _sec_to_mmss(latest_y) if mmss else f"{latest_y:.2f}秒"
    _annotate_latest(ax, df["date"].iloc[-1], latest_y, label)

    return fig


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rank"], label="学年順位", color="tab:red", marker="o")
    ax2.plot(df["date"], df["deviation"], label="偏差値", color="tab:blue", marker="o")

    _setup_ax(
        ax1,
        f"学業成績の推移（{period}）",
        ylabel_left="学年順位",
        ylabel_right="偏差値",
    )

    _annotate_latest(ax1, df["date"].iloc[-1], df["rank"].iloc[-1], f"{int(df['rank'].iloc[-1])}位")
    _annotate_latest(ax2, df["date"].iloc[-1], df["deviation"].iloc[-1], f"{df['deviation'].iloc[-1]:.1f}")

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    return fig


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rating"], label="評点", color="black", linewidth=2, marker="o")

    subject_labels = {
        "score_jp": "国語",
        "score_math": "数学",
        "score_en": "英語",
        "score_sci": "理科",
        "score_soc": "社会",
    }

    for col, label in subject_labels.items():
        if col in df.columns:
            ax2.plot(df["date"], df[col], label=label, marker="o")

    _setup_ax(
        ax1,
        f"評点・教科別スコアの推移（{period}）",
        ylabel_left="評点",
        ylabel_right="教科スコア",
    )

    _annotate_latest(ax1, df["date"].iloc[-1], df["rating"].iloc[-1], f"{df['rating'].iloc[-1]:.1f}")

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)

    return fig
