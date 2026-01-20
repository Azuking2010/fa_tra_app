# modules/report/chart_base.py
from __future__ import annotations

import os
import colorsys
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Tuple

try:
    import matplotlib.pyplot as plt
    import matplotlib.ticker as mticker
    from matplotlib.ticker import FuncFormatter
    from matplotlib import font_manager
    from matplotlib.colors import to_rgb
    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False

from .chart_config import BASE_COLORS, ROADMAP_SHADE, ROADMAP_STYLE, ChartSpec, SeriesSpec


def _require_mpl():
    if not HAS_MPL:
        raise ModuleNotFoundError("matplotlib is required for report charts, but it is not installed.")


# =========================================================
# フォント（Noto Sans JPを優先）
# - Streamlit Cloud / Local どちらでも動くように
# =========================================================
def setup_japanese_font(
    font_path_candidates: Optional[List[str]] = None,
    prefer_family: str = "Noto Sans JP",
) -> None:
    """
    - font_path_candidates: TTFの候補パス一覧（存在するものを使う）
    - prefer_family: フォールバックとして設定するfont family名
    """
    _require_mpl()

    # デフォルト候補（あなたの配置に寄せる）
    candidates = font_path_candidates or [
        # repoルート基準（Streamlit Cloud）
        os.path.join("assets", "fonts", "Noto_Sans_JP", "static", "NotoSansJP-Regular.ttf"),
        os.path.join("assets", "fonts", "NotoSansJP-VariableFont_wght.ttf"),
        # Windows ローカル例（ユーザー提示の場所）
        os.path.join("D:\\", "fa_tra_app", "assets", "fonts", "Noto_Sans_JP", "static", "NotoSansJP-Regular.ttf"),
    ]

    for p in candidates:
        try:
            if p and os.path.exists(p):
                font_manager.fontManager.addfont(p)
                fam = font_manager.FontProperties(fname=p).get_name()
                plt.rcParams["font.family"] = fam
                plt.rcParams["axes.unicode_minus"] = False
                return
        except Exception:
            continue

    # ファイルが見つからない場合はfamily名だけ指定（環境依存）
    plt.rcParams["font.family"] = prefer_family
    plt.rcParams["axes.unicode_minus"] = False


# =========================================================
# ユーティリティ
# =========================================================
def mmss_from_seconds(sec: float) -> str:
    if sec is None:
        return ""
    try:
        sec_i = int(round(float(sec)))
    except Exception:
        return ""
    m = sec_i // 60
    s = sec_i % 60
    return f"{m}:{s:02d}"


def mmss_formatter():
    def _fmt(y, _pos):
        return mmss_from_seconds(y)
    return FuncFormatter(_fmt)


def _ticks_from_range(ymin: float, ymax: float, step: float) -> List[float]:
    # ymin > ymax（逆向き）も普通に作れるように
    ticks: List[float] = []
    if step <= 0:
        return ticks

    if ymin <= ymax:
        v = ymin
        while v <= ymax + 1e-9:
            ticks.append(round(v, 10))
            v += step
    else:
        v = ymin
        while v >= ymax - 1e-9:
            ticks.append(round(v, 10))
            v -= step
    return ticks


def _color_to_rgb(color: str) -> Tuple[float, float, float]:
    return to_rgb(color)


def _shade_color(color: str, factor: float) -> Tuple[float, float, float]:
    """
    factor:
      1.0 そのまま
      <1.0 暗い
      >1.0 明るい（上限1.0でクリップ）
    """
    r, g, b = _color_to_rgb(color)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    v2 = max(0.0, min(1.0, v * factor))
    r2, g2, b2 = colorsys.hsv_to_rgb(h, s, v2)
    return (r2, g2, b2)


def _annotate_last(ax, x_last, y_last, text: str):
    # 右端で見切れにくいように少し左に寄せる
    ax.annotate(
        text,
        xy=(x_last, y_last),
        xytext=(6, 0),
        textcoords="offset points",
        va="center",
        fontsize=9,
        alpha=0.9,
    )


def _period_text(df, x_col: str) -> str:
    if df is None or len(df) == 0 or x_col not in df.columns:
        return ""
    x0 = df[x_col].min()
    x1 = df[x_col].max()
    try:
        return f"{x0} ～ {x1}"
    except Exception:
        return ""


# =========================================================
# ROADMAP overlay（可能なら描画）
# - report側の構造が不明なので「取れたら描く」方式で安全に。
# =========================================================
def try_draw_roadmap_bands(
    ax,
    report: Any,
    chart_id: str,
    x_values: List[Any],
    base_color: str,
):
    """
    想定：
      report.roadmap は dict または DataFrame 的なもの
      chart_id と metric が紐づいて low/mid/high が取れる場合に線を引く
    取れない場合は何もしない（アプリを壊さない）
    """
    if report is None:
        return

    # 1) dict形式の想定例：report.roadmap.get(chart_id) -> {"low":..,"mid":..,"high":..}
    roadmap = getattr(report, "roadmap", None)
    if roadmap is None:
        return

    try:
        item = roadmap.get(chart_id) if hasattr(roadmap, "get") else None
        if not isinstance(item, dict):
            return
        for level in ["low", "mid", "high"]:
            if level not in item:
                continue
            y = item[level]
            c = _shade_color(base_color, ROADMAP_SHADE[level])
            ax.plot(
                x_values,
                [y] * len(x_values),
                color=c,
                **ROADMAP_STYLE,
            )
    except Exception:
        return


# =========================================================
# ベース：単軸/双軸 折れ線グラフ
# =========================================================
def make_line_chart_single_axis(report: Any, df, spec: ChartSpec, show_roadmap: bool = True):
    _require_mpl()

    x_col = spec.x_col
    if df is None or len(df) == 0:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.set_title(spec.title)
        ax.text(0.5, 0.5, "データがありません", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, ax = plt.subplots(figsize=(8, 4))
    x = df[x_col].tolist()

    # 期間をタイトルに2行で表示
    period = _period_text(df, x_col)
    title = spec.title if not period else f"{spec.title}\n{period}"
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)

    # 軸設定
    ax.set_ylabel(spec.left_axis.label)
    ax.set_ylim(spec.left_axis.ymin, spec.left_axis.ymax)
    ticks = _ticks_from_range(spec.left_axis.ymin, spec.left_axis.ymax, spec.left_axis.step)
    if ticks:
        ax.set_yticks(ticks)

    if spec.y_mmss:
        ax.yaxis.set_major_formatter(mmss_formatter())

    # series
    for s in spec.series_left:
        if s.col not in df.columns:
            continue
        y = df[s.col].tolist()
        color = BASE_COLORS.get(s.color_key, "tab:blue")
        ax.plot(
            x, y,
            label=s.label,
            color=color,
            linestyle=s.linestyle,
            linewidth=s.linewidth,
            marker=s.marker,
        )

        # 最新値注釈
        if spec.annotate_last and len(x) > 0:
            x_last = x[-1]
            y_last = y[-1]
            text = mmss_from_seconds(y_last) if spec.y_mmss else f"{y_last:g}"
            _annotate_last(ax, x_last, y_last, text)

        # ROADMAP（最初の系列の色を基準に）
        if show_roadmap:
            try_draw_roadmap_bands(ax, report, spec.chart_id, x, color)

    ax.legend(loc="upper right")
    return fig


def make_line_chart_dual_axis(report: Any, df, spec: ChartSpec, show_roadmap: bool = True):
    _require_mpl()

    x_col = spec.x_col
    if df is None or len(df) == 0:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.set_title(spec.title)
        ax.text(0.5, 0.5, "データがありません", ha="center", va="center")
        ax.axis("off")
        return fig

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    x = df[x_col].tolist()

    period = _period_text(df, x_col)
    title = spec.title if not period else f"{spec.title}\n{period}"
    ax1.set_title(title)

    ax1.grid(True, axis="y", alpha=0.3)

    # 左軸
    ax1.set_ylabel(spec.left_axis.label)
    ax1.set_ylim(spec.left_axis.ymin, spec.left_axis.ymax)
    ticks1 = _ticks_from_range(spec.left_axis.ymin, spec.left_axis.ymax, spec.left_axis.step)
    if ticks1:
        ax1.set_yticks(ticks1)

    # 右軸
    if spec.right_axis is not None:
        ax2.set_ylabel(spec.right_axis.label)
        ax2.set_ylim(spec.right_axis.ymin, spec.right_axis.ymax)
        ticks2 = _ticks_from_range(spec.right_axis.ymin, spec.right_axis.ymax, spec.right_axis.step)
        if ticks2:
            ax2.set_yticks(ticks2)

    # 左系列
    for s in spec.series_left:
        if s.col not in df.columns:
            continue
        y = df[s.col].tolist()
        color = BASE_COLORS.get(s.color_key, "tab:blue")
        ax1.plot(
            x, y,
            label=s.label,
            color=color,
            linestyle=s.linestyle,
            linewidth=s.linewidth,
            marker=s.marker,
        )

        if spec.annotate_last and len(x) > 0:
            x_last = x[-1]
            y_last = y[-1]
            text = mmss_from_seconds(y_last) if spec.y_mmss else f"{y_last:g}"
            _annotate_last(ax1, x_last, y_last, text)

        if show_roadmap:
            try_draw_roadmap_bands(ax1, report, spec.chart_id, x, color)

    # 右系列
    if spec.series_right:
        for s in spec.series_right:
            if s.col not in df.columns:
                continue
            y = df[s.col].tolist()
            color = BASE_COLORS.get(s.color_key, "tab:orange")
            ax2.plot(
                x, y,
                label=s.label,
                color=color,
                linestyle=s.linestyle,
                linewidth=s.linewidth,
                marker=s.marker,
            )

            if spec.annotate_last and len(x) > 0:
                x_last = x[-1]
                y_last = y[-1]
                text = mmss_from_seconds(y_last) if spec.y_mmss else f"{y_last:g}"
                _annotate_last(ax2, x_last, y_last, text)

    # 凡例（左右分け）
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)

    return fig
