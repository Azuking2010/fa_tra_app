# modules/report/report_charts.py
from __future__ import annotations

# matplotlib は環境によって無いことがあるので optional
try:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:
    plt = None
    FuncFormatter = None
    HAS_MPL = False


# ---------------------------------------------------------
# 新方式（chart_base / chart_config）が存在すればそれを使う
# 存在しなければフォールバック（最低限のグラフ）でアプリを落とさない
# ---------------------------------------------------------
HAS_NEW_CHARTS = False
CHARTS = None
_setup_japanese_font = None
_make_single = None
_make_dual = None
_mmss_from_seconds = None

try:
    from .chart_config import CHARTS as _CHARTS
    from .chart_base import (
        setup_japanese_font as _setup_japanese_font_impl,
        make_line_chart_single_axis as _make_single_impl,
        make_line_chart_dual_axis as _make_dual_impl,
        mmss_from_seconds as _mmss_from_seconds_impl,
    )
    CHARTS = _CHARTS
    _setup_japanese_font = _setup_japanese_font_impl
    _make_single = _make_single_impl
    _make_dual = _make_dual_impl
    _mmss_from_seconds = _mmss_from_seconds_impl
    HAS_NEW_CHARTS = True
except Exception:
    # Cloud側にchart_base/chart_configが未反映でもアプリを落とさないため握りつぶす
    HAS_NEW_CHARTS = False


# =========================================================
# フォールバック用（最低限）
# =========================================================
def _fallback_mmss(sec: float) -> str:
    try:
        sec_i = int(round(float(sec)))
    except Exception:
        return ""
    m = sec_i // 60
    s = sec_i % 60
    return f"{m}:{s:02d}"


def _fallback_mmss_formatter():
    def _fmt(y, _pos):
        return _fallback_mmss(y)
    return FuncFormatter(_fmt)


def _fallback_empty_fig(title: str, msg: str):
    if not HAS_MPL:
        return None
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.set_title(title)
    ax.text(0.5, 0.5, msg, ha="center", va="center")
    ax.axis("off")
    return fig


# =========================================================
# 公開関数（既存互換）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    """
    互換維持：P2 フィジカル（身長/体重）
    新方式があればConfig通りで描画
    無ければ最低限で描画（BMIは省略）
    """
    if not HAS_MPL:
        return None

    if HAS_NEW_CHARTS:
        _setup_japanese_font()
        spec = CHARTS["physical_hw"]
        df = report.portfolio
        return _make_dual(report, df, spec, show_roadmap=show_roadmap)

    # --- fallback ---
    df = getattr(report, "portfolio", None)
    if df is None or len(df) == 0:
        return _fallback_empty_fig("フィジカル推移（身長・体重）", "データがありません")

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()

    x = df["date"].tolist() if "date" in df.columns else list(range(len(df)))
    if "height_cm" in df.columns:
        ax1.plot(x, df["height_cm"].tolist(), marker="o", label="身長（cm）")
    if "weight_kg" in df.columns:
        ax2.plot(x, df["weight_kg"].tolist(), marker="o", label="体重（kg）")

    ax1.set_title("フィジカル推移（身長・体重）")
    ax1.set_ylabel("身長（cm）")
    ax2.set_ylabel("体重（kg）")
    ax1.grid(True, axis="y", alpha=0.3)
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)
    return fig


def fig_run_metric(report, metric: str, title: str, show_roadmap: bool = True, mmss: bool = False):
    """
    互換維持：走力系
    """
    if not HAS_MPL:
        return None

    if HAS_NEW_CHARTS:
        _setup_japanese_font()
        m = (metric or "").lower()
        if "50" in m:
            spec = CHARTS["run_50m"]
        elif "1500" in m:
            spec = CHARTS["run_1500m"]
        elif "3000" in m:
            spec = CHARTS["run_3000m"]
        else:
            # 不明な場合は簡易
            df = report.portfolio
            fig, ax = plt.subplots(figsize=(8, 4))
            if "date" in df.columns and metric in df.columns:
                ax.plot(df["date"], df[metric], marker="o")
            ax.set_title(title)
            ax.set_ylabel("タイム")
            ax.grid(True, axis="y", alpha=0.3)
            return fig

        df = report.portfolio
        return _make_single(report, df, spec, show_roadmap=show_roadmap)

    # --- fallback ---
    df = getattr(report, "portfolio", None)
    if df is None or len(df) == 0:
        return _fallback_empty_fig(title, "データがありません")

    if "date" not in df.columns or metric not in df.columns:
        return _fallback_empty_fig(title, f"列が見つかりません: {metric}")

    fig, ax = plt.subplots(figsize=(8, 4))
    x = df["date"].tolist()
    y = df[metric].tolist()

    ax.plot(x, y, marker="o")
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)

    # mm:ss 表示（1500/3000を想定）
    if mmss and FuncFormatter is not None:
        ax.yaxis.set_major_formatter(_fallback_mmss_formatter())
        ax.set_ylabel("タイム（分:秒）")
    else:
        ax.set_ylabel("タイム")

    # 最新値注釈
    if len(x) > 0:
        txt = _fallback_mmss(y[-1]) if mmss else f"{y[-1]}"
        ax.annotate(txt, xy=(x[-1], y[-1]), xytext=(6, 0), textcoords="offset points", va="center", fontsize=9)

    return fig


def fig_academic_position(report, show_roadmap: bool = True):
    if not HAS_MPL:
        return None

    if HAS_NEW_CHARTS:
        _setup_japanese_font()
        spec = CHARTS["academic_rank_dev"]
        df = report.portfolio
        return _make_dual(report, df, spec, show_roadmap=show_roadmap)

    return _fallback_empty_fig("学業：学年順位・偏差値（参考）", "chart_base 未反映のため簡易表示は未実装")


def fig_academic_scores_rating(report, show_roadmap: bool = True):
    if not HAS_MPL:
        return None

    if HAS_NEW_CHARTS:
        _setup_japanese_font()
        spec = CHARTS["academic_rating_scores"]
        df = report.portfolio
        return _make_dual(report, df, spec, show_roadmap=show_roadmap)

    return _fallback_empty_fig("学業：評点・教科得点", "chart_base 未反映のため簡易表示は未実装")
