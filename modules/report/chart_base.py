# modules/report/chart_base.py
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

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


def _ensure_dt(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    dff = df.copy()
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


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """
    dataclass/obj の attribute と dict の両方に対応して値を取る。
    グラフ定義が「型混在」しても落とさないための防波堤。
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def build_line_chart(
    df: pd.DataFrame,
    chart_spec,
    period_text: str = "",
    roadmap: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    show_latest_annotation: bool = False,  # ← report_charts.py が渡してくるので必須
):
    """
    chart_spec: chart_config.py の ChartSpec（または互換のdict/obj）
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

    right_axis = _get(chart_spec, "right_axis", None)
    ax2 = ax.twinx() if right_axis else None

    # タイトル
    title = str(_get(chart_spec, "title", ""))
    if period_text:
        title = f"{title}\n{period_text}" if title else str(period_text)
    ax.set_title(title)

    # X軸
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    for label in ax.get_xticklabels():
        label.set_rotation(0)

    # 軸ラベル（無い場合は空でOK）
    left_axis = _get(chart_spec, "left_axis", None)
    ax.set_ylabel(str(_get(left_axis, "label", "")))
    if ax2 is not None:
        ax2.set_ylabel(str(_get(right_axis, "label", "")))

    # ---- Y軸スケール（config準拠 / dictでも落ちない）----
    def _apply_axis_scale(_ax, axis_spec):
        if axis_spec is None:
            return

        ymin = _get(axis_spec, "ymin", None)
        ymax = _get(axis_spec, "ymax", None)

        # ymin/ymax がどちらか欠けてたら set_ylim しない（落とさない）
        if ymin is not None and ymax is not None:
            invert = bool(_get(axis_spec, "invert", False))
            if invert:
                _ax.set_ylim(ymax, ymin)
            else:
                _ax.set_ylim(ymin, ymax)

        major_tick = _get(axis_spec, "major_tick", None)
        minor_tick = _get(axis_spec, "minor_tick", None)

        # 目盛り（数値として成立するものだけ）
        try:
            if major_tick is not None and float(major_tick) > 0:
                _ax.yaxis.set_major_locator(MultipleLocator(float(major_tick)))
        except Exception:
            pass

        try:
            if minor_tick is not None and float(minor_tick) > 0:
                _ax.yaxis.set_minor_locator(MultipleLocator(float(minor_tick)))
        except Exception:
            pass

        _ax.grid(True, axis="y", which="major", linestyle="-", alpha=0.25)
        _ax.grid(True, axis="y", which="minor", linestyle=":", alpha=0.15)

    _apply_axis_scale(ax, left_axis)
    if ax2 is not None:
        _apply_axis_scale(ax2, right_axis)

    # 秒 → mm:ss 表示
    if _get(left_axis, "formatter", None) == "mmss":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: _format_mmss(x)))
    if ax2 is not None and _get(right_axis, "formatter", None) == "mmss":
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: _format_mmss(x)))

    # ---- 実データ系列 ----
    colors = _get(
        chart_spec,
        "palette",
        ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"),
    )

    plotted_last_points = []  # 注釈用
    series_list = _get(chart_spec, "series", []) or []

    for i, s in enumerate(series_list):
        y_col = _get(s, "col", None)
        if not y_col or y_col not in dff.columns:
            continue

        x = dff[date_col]
        y = pd.to_numeric(dff[y_col], errors="coerce")

        axis_side = _get(s, "axis", "left")
        tgt_ax = ax2 if (ax2 is not None and axis_side == "right") else ax

        color = _pick_color(colors, i)

        tgt_ax.plot(
            x,
            y,
            label=str(_get(s, "label", y_col)),
            linewidth=_get(s, "width", 2.2) or 2.2,
            linestyle=_get(s, "linestyle", "-") or "-",
            marker=_get(s, "marker", "o") or "o",
            markersize=_get(s, "marker_size", 4.8) or 4.8,
            color=color,
        )

        # 最新点（オプション）
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
    if roadmap and roadmap_keys and isinstance(roadmap_keys, (list, tuple)) and len(roadmap_keys) == 3:
        low_key, mid_key, high_key = roadmap_keys

        xs = []
        low_vals, mid_vals, high_vals = [], [], []

        for ym, row in (roadmap or {}).items():
            try:
                dt = pd.to_datetime(f"{ym}-01", errors="coerce")
            except Exception:
                dt = pd.NaT
            if pd.isna(dt):
                continue

            xs.append(dt)
            low_vals.append((row or {}).get(low_key))
            mid_vals.append((row or {}).get(mid_key))
            high_vals.append((row or {}).get(high_key))

        tgt = ax
        if ax2 is not None and _get(chart_spec, "roadmap_axis", "left") == "right":
            tgt = ax2

        def _plot_rm(vals, style: str, alpha: float):
            v = pd.to_numeric(pd.Series(vals), errors="coerce")
            tgt.plot(xs, v, linestyle=style, linewidth=1.2, alpha=alpha)

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

    # 最新値注釈（簡易）
    if plotted_last_points:
        for tgt_ax, x0, y0, s, color in plotted_last_points:
            try:
                # mmss 指定なら mmss、そうでなければ数値
                use_mmss = False
                if tgt_ax is ax and _get(left_axis, "formatter", None) == "mmss":
                    use_mmss = True
                if ax2 is not None and tgt_ax is ax2 and _get(right_axis, "formatter", None) == "mmss":
                    use_mmss = True

                if use_mmss:
                    txt = _format_mmss(y0)
                else:
                    try:
                        txt = f"{float(y0):.2f}".rstrip("0").rstrip(".")
                    except Exception:
                        txt = str(y0)

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
