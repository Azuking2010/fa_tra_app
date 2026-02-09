# modules/report/chart_base.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Iterable, List

import pandas as pd


def require_mpl():
    """
    matplotlib は Streamlit Cloud でも動く前提。
    import コストを抑えるため遅延 import にする。
    """
    import matplotlib.pyplot as plt  # noqa
    return plt


def apply_jp_font():
    """
    assets/fonts/Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf を使う。
    フォントが無い/読めない環境でも落とさず、デフォルトにフォールバック。
    """
    plt = require_mpl()
    try:
        import matplotlib.font_manager as fm

        base = Path(__file__).resolve().parents[2]  # fa_tra_app/
        font_path = base / "assets" / "fonts" / "Noto_Sans_JP" / "NotoSansJP-VariableFont_wght.ttf"
        if font_path.exists():
            fp = fm.FontProperties(fname=str(font_path))
            # グローバル設定（表示の一貫性優先）
            import matplotlib as mpl

            mpl.rcParams["font.family"] = fp.get_name()
    except Exception:
        # フォント設定失敗しても落とさない
        pass
    return plt


# -------------------------
# Spec アクセスの揺れ吸収
# -------------------------
def _get(obj: Any, key: str, default: Any = None) -> Any:
    """obj が dict / dataclass / 通常オブジェクト どれでも key を取り出す"""
    if obj is None:
        return default
    try:
        if isinstance(obj, dict):
            return obj.get(key, default)
        if hasattr(obj, key):
            return getattr(obj, key)
    except Exception:
        return default
    return default


def _ensure_dt(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    dff = df.copy() if df is not None else pd.DataFrame()
    if date_col not in dff.columns:
        dff[date_col] = pd.NaT
    dff[date_col] = pd.to_datetime(dff[date_col], errors="coerce")
    dff = dff.sort_values(date_col).reset_index(drop=True)
    return dff


def _pick_color(colors: Tuple[str, ...], idx: int) -> str:
    if not colors:
        return "#1f77b4"
    return colors[idx % len(colors)]


def _format_mmss(sec: Any) -> str:
    try:
        if sec is None:
            return ""
        v = float(sec)
        if v != v:  # NaN
            return ""
        m = int(v // 60)
        s = int(round(v - m * 60))
        return f"{m}:{s:02d}"
    except Exception:
        return ""


def build_line_chart(
    df: pd.DataFrame,
    chart_spec: Any,
    period_text: str = "",
    roadmap: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    show_latest_annotation: bool = False,  # report_charts.py が渡してくるので受ける
):
    """
    chart_spec: chart_config.py の ChartSpec（または dict 互換）
    roadmap: ym -> {col_low/col_mid/col_high: value, ...}
    """
    # 遅延 import
    plt = apply_jp_font()
    import matplotlib.ticker as mticker
    from matplotlib.ticker import MultipleLocator
    from matplotlib.dates import DateFormatter, AutoDateLocator

    date_col = _get(chart_spec, "date_col", "date")
    dff = _ensure_dt(df, date_col)

    # Figure/Axes
    fig = plt.figure(figsize=(10.8, 4.6))
    ax = fig.add_subplot(111)

    right_axis_spec = _get(chart_spec, "right_axis", None)
    ax2 = ax.twinx() if right_axis_spec else None

    # タイトル
    title = _get(chart_spec, "title", "")
    if title is None:
        title = ""
    if period_text:
        title = f"{title}\n{period_text}" if title else f"{period_text}"
    ax.set_title(title)

    # X軸
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    for label in ax.get_xticklabels():
        label.set_rotation(0)

    # 軸ラベル（無い場合でも落とさない）
    left_axis_spec = _get(chart_spec, "left_axis", None)
    ax.set_ylabel(_get(left_axis_spec, "label", "") or "")

    if ax2 is not None:
        ax2.set_ylabel(_get(right_axis_spec, "label", "") or "")

    # ---- Y軸スケール（config準拠）----
    def _apply_axis_scale(_ax, axis_spec):
        if axis_spec is None:
            return

        ymin = _get(axis_spec, "ymin", None)
        ymax = _get(axis_spec, "ymax", None)
        invert = bool(_get(axis_spec, "invert", False))

        # ymin/ymax が両方ある時だけ set_ylim（片方欠けても落とさない）
        if ymin is not None and ymax is not None:
            if invert:
                _ax.set_ylim(ymax, ymin)
            else:
                _ax.set_ylim(ymin, ymax)

        # 目盛り（major/minor）: 無い/0/None はスキップ
        major_tick = _get(axis_spec, "major_tick", None)
        minor_tick = _get(axis_spec, "minor_tick", None)

        try:
            if major_tick:
                _ax.yaxis.set_major_locator(MultipleLocator(float(major_tick)))
            if minor_tick:
                _ax.yaxis.set_minor_locator(MultipleLocator(float(minor_tick)))
        except Exception:
            # tick 指定が壊れていても落とさない
            pass

        _ax.grid(True, axis="y", which="major", linestyle="-", alpha=0.25)
        _ax.grid(True, axis="y", which="minor", linestyle=":", alpha=0.15)

    _apply_axis_scale(ax, left_axis_spec)
    if ax2 is not None:
        _apply_axis_scale(ax2, right_axis_spec)

    # 秒 → mm:ss 表示
    if _get(left_axis_spec, "formatter", None) == "mmss":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: _format_mmss(x)))
    if ax2 is not None and _get(right_axis_spec, "formatter", None) == "mmss":
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: _format_mmss(x)))

    # ---- 実データ系列 ----
    colors = _get(
        chart_spec,
        "palette",
        ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"),
    )

    series_list = _get(chart_spec, "series", []) or []
    plotted_last_points = []  # 注釈用

    for i, s in enumerate(series_list):
        y_col = _get(s, "col", None)
        if not y_col or y_col not in dff.columns:
            continue

        x = dff[date_col]
        y = pd.to_numeric(dff[y_col], errors="coerce")

        axis_side = _get(s, "axis", "left")
        tgt_ax = ax2 if (ax2 is not None and axis_side == "right") else ax
        color = _pick_color(colors, i)

        label = _get(s, "label", y_col)

        linewidth = _get(s, "width", None) or 2.2
        linestyle = _get(s, "linestyle", None) or "-"
        marker = _get(s, "marker", None) or "o"
        markersize = _get(s, "marker_size", None) or 4.8

        tgt_ax.plot(
            x,
            y,
            label=label,
            linewidth=linewidth,
            linestyle=linestyle,
            marker=marker,
            markersize=markersize,
            color=color,
        )

        # 最新点
        if show_latest_annotation and bool(_get(chart_spec, "latest_annotation", False)):
            try:
                valid = y.dropna()
                if len(valid) > 0:
                    last_idx = valid.index[-1]
                    plotted_last_points.append((tgt_ax, x.loc[last_idx], y.loc[last_idx], s, color))
            except Exception:
                pass

    # ---- ROADMAP（low/mid/high）を点線で重ねる（指定がある時だけ）----
    roadmap_keys = _get(chart_spec, "roadmap_keys", None)
    if roadmap and roadmap_keys:
        # roadmap_keys: (low_col, mid_col, high_col)
        try:
            low_key, mid_key, high_key = roadmap_keys
        except Exception:
            low_key = mid_key = high_key = None

        xs: List[pd.Timestamp] = []
        low_vals: List[Any] = []
        mid_vals: List[Any] = []
        high_vals: List[Any] = []

        for ym, row in roadmap.items():
            try:
                dt = pd.to_datetime(f"{ym}-01", errors="coerce")
            except Exception:
                dt = pd.NaT
            if pd.isna(dt):
                continue
            xs.append(dt)
            rowd = row if isinstance(row, dict) else {}
            low_vals.append(rowd.get(low_key) if low_key else None)
            mid_vals.append(rowd.get(mid_key) if mid_key else None)
            high_vals.append(rowd.get(high_key) if high_key else None)

        # どっちの軸に出すか
        tgt = ax
        if ax2 is not None and _get(chart_spec, "roadmap_axis", "left") == "right":
            tgt = ax2

        def _plot_rm(vals, style: str, alpha: float):
            try:
                v = pd.to_numeric(pd.Series(vals), errors="coerce")
                tgt.plot(xs, v, linestyle=style, linewidth=1.2, alpha=alpha)
            except Exception:
                pass

        _plot_rm(low_vals, ":", 0.55)
        _plot_rm(mid_vals, "--", 0.55)
        _plot_rm(high_vals, ":", 0.55)

    # 凡例（左右の系列を統合）
    handles, labels = ax.get_legend_handles_labels()
    if ax2 is not None:
        h2, l2 = ax2.get_legend_handles_labels()
        handles += h2
        labels += l2
    if handles:
        ax.legend(handles, labels, loc="upper right", frameon=True)

    # 最新値注釈（mmss or 数値）
    if plotted_last_points:
        for tgt_ax, x0, y0, s, color in plotted_last_points:
            try:
                # formatter が mmss なら mmss、そうでなければ数値
                is_mmss = False
                try:
                    fmt = tgt_ax.yaxis.get_major_formatter()
                    is_mmss = isinstance(fmt, mticker.FuncFormatter) and (_get(_get(chart_spec, "left_axis"), "formatter") == "mmss" or _get(_get(chart_spec, "right_axis"), "formatter") == "mmss")
                except Exception:
                    is_mmss = False

                if is_mmss:
                    txt = _format_mmss(y0)
                else:
                    txt = f"{float(y0):.2f}".rstrip("0").rstrip(".")
                tgt_ax.annotate(
                    txt,
                    xy=(x0, y0),
                    xytext=(6, 0),
                    textcoords="offset points",
                    va="center",
                    fontsize=9,
                    color=color,
                )
            except Exception:
                pass

    fig.tight_layout()
    return fig
