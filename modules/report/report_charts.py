# modules/report/report_charts.py
from __future__ import annotations

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False

from .charts_base import (
    require_mpl,
    apply_jp_font_auto,
    setup_ax,
    build_period_text,
    annotate_latest,
    seconds_to_mmss,
    apply_mmss_yaxis,
)

# import 時に必ず日本語フォントを適用（再発防止）
_JP_FONT_RESULT = None
if HAS_MPL:
    _JP_FONT_RESULT = apply_jp_font_auto()


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    require_mpl()

    df = report.portfolio

    period = build_period_text(df)
    title = "フィジカル推移（身長・体重・BMI）"
    if period:
        title = f"{title}\n{period}"

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2  # util 用

    # 折線
    ax1.plot(df["date"], df["height_cm"], label="身長（cm）", marker="o")
    ax2.plot(df["date"], df["weight_kg"], label="体重（kg）", marker="o", linestyle="-")

    if "bmi" in df.columns:
        ax2.plot(df["date"], df["bmi"], label="BMI", linestyle="--")

    setup_ax(ax1, title, "身長（cm）", "体重（kg） / BMI")

    # 最新値注釈
    try:
        last = df.iloc[-1]
        annotate_latest(ax1, last["date"], last["height_cm"], f'{float(last["height_cm"]):.1f}cm')
        annotate_latest(ax2, last["date"], last["weight_kg"], f'{float(last["weight_kg"]):.1f}kg', dx=6, dy=-10)
        if "bmi" in df.columns:
            annotate_latest(ax2, last["date"], last["bmi"], f'BMI {float(last["bmi"]):.1f}', dx=6, dy=10)
    except Exception:
        pass

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    fig.tight_layout()
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
    require_mpl()

    df = report.portfolio

    period = build_period_text(df)
    # タイトル日本語化（呼び出し側が英語でもここで整える）
    title_map = {
        "Run: 50m": "50m走",
        "Run: 1500m": "1500m走",
        "Run: 3000m": "3000m走",
        "50m": "50m走",
        "1500m": "1500m走",
        "3000m": "3000m走",
    }
    base_title = title_map.get(title, title)
    if period:
        full_title = f"{base_title}\n{period}"
    else:
        full_title = base_title

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["date"], df[metric], marker="o")

    ax.set_title(full_title)
    ax.grid(True, axis="y", alpha=0.3)

    # 50m は秒表示、1500/3000 は mm:ss 表示
    # ※データは秒のまま。表示だけ mm:ss にするのが正解。
    if mmss:
        ax.set_ylabel("タイム（分:秒）")
        apply_mmss_yaxis(ax)
    else:
        ax.set_ylabel("タイム（秒）")

    # 最新値注釈
    try:
        last = df.iloc[-1]
        v = last[metric]
        if mmss:
            txt = seconds_to_mmss(v)
        else:
            txt = f"{float(v):.1f}s" if float(v) != int(float(v)) else f"{int(float(v))}s"
        annotate_latest(ax, last["date"], v, txt)
    except Exception:
        pass

    fig.tight_layout()
    return fig


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    require_mpl()

    df = report.portfolio

    period = build_period_text(df)
    title = "学業推移（学年順位・偏差値）"
    if period:
        title = f"{title}\n{period}"

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rank"], label="学年順位", marker="o")
    ax2.plot(df["date"], df["deviation"], label="偏差値", marker="o")

    setup_ax(ax1, title, "学年順位（小さいほど良い）", "偏差値")

    # 最新値注釈
    try:
        last = df.iloc[-1]
        annotate_latest(ax1, last["date"], last["rank"], f'{int(last["rank"])}位')
        annotate_latest(ax2, last["date"], last["deviation"], f'{float(last["deviation"]):.1f}', dx=6, dy=-10)
    except Exception:
        pass

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    fig.tight_layout()
    return fig


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    require_mpl()

    df = report.portfolio

    period = build_period_text(df)
    title = "学業：評点・教科スコア"
    if period:
        title = f"{title}\n{period}"

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    # 評点（左）
    ax1.plot(df["date"], df["rating"], label="評点", linewidth=2, marker="o")

    # 教科スコア（右）
    subject_map = {
        "score_jp": "国語",
        "score_math": "数学",
        "score_en": "英語",
        "score_sci": "理科",
        "score_soc": "社会",
    }
    for col, jp in subject_map.items():
        if col in df.columns:
            ax2.plot(df["date"], df[col], label=jp, marker="o")

    setup_ax(ax1, title, "評点", "得点")

    # 最新値注釈（評点だけ）
    try:
        last = df.iloc[-1]
        annotate_latest(ax1, last["date"], last["rating"], f'{float(last["rating"]):.1f}')
    except Exception:
        pass

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)

    fig.tight_layout()
    return fig
