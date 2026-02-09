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


def build_line_chart(
    df: pd.DataFrame,
    chart_spec,
    period_text: str = "",
    roadmap: Optional[Dict[str, Dict[str, Any]]] = None,
    *,
    show_latest_annotation: bool = False,  # ← report_charts.py が渡してくるので必須
):
    """
    chart_spec: chart_config.py の ChartSpec
    roadmap: ym -> {col_low/col_mid/col_high: value, ...}
    """
    # 遅延 import
    plt = apply_jp_font()
    import matplotlib.ticker as mticker
    from matplotlib.dates import AutoDateLocator, DateFormatter
    from matplotlib.ticker import MultipleLocator

    dff = _ensure_dt(df, chart_spec.date_col)

    # Figure/Axes
    fig = plt.figure(figsize=(10.8, 4.6))
    ax = fig.add_subplot(111)
    ax2 = ax.twinx() if chart_spec.right_axis else None

    # タイトル
    title = chart_spec.title
    if period_text:
        title = f"{title}\n{period_text}"
    ax.set_title(title)

    # X軸
    ax.xaxis.set_major_locator(AutoDateLocator())
    ax.xaxis.set_major_formatter(DateFormatter("%Y-%m-%d"))
    for label in ax.get_xticklabels():
        label.set_rotation(0)

    # 軸ラベル
    ax.set_ylabel(chart_spec.left_axis.label)
    if ax2 is not None:
        ax2.set_ylabel(chart_spec.right_axis.label)

    # ---- Y軸スケール（config準拠）----
    def _axis_get(axis_spec, key: str, default=None):
        """
        axis_spec が dataclass/obj でも dict でも安全に読む。
        """
        if axis_spec is None:
            return default
        if isinstance(axis_spec, dict):
            return axis_spec.get(key, default)
        return getattr(axis_spec, key, default)

    def _apply_axis_scale(_ax, axis_spec):
        if axis_spec is None:
            return

        ymin = _axis_get(axis_spec, "ymin", None)
        ymax = _axis_get(axis_spec, "ymax", None)
        invert = bool(_axis_get(axis_spec, "invert", False))

        # ymin/ymax が揃っている場合のみ ylim を設定
        if ymin is not None and ymax is not None:
            if invert:
                _ax.set_ylim(ymax, ymin)
            else:
                _ax.set_ylim(ymin, ymax)

        # 目盛り（major/minor）: 存在しない設定は無視（落とさない）
        major_tick = _axis_get(axis_spec, "major_tick", None)
        minor_tick = _axis_get(axis_spec, "minor_tick", None)

        try:
            if major_tick:
                _ax.yaxis.set_major_locator(MultipleLocator(major_tick))
        except Exception:
            pass

        try:
            if minor_tick:
                _ax.yaxis.set_minor_locator(MultipleLocator(minor_tick))
        except Exception:
            pass

        _ax.grid(True, axis="y", which="major", linestyle="-", alpha=0.25)
        _ax.grid(True, axis="y", which="minor", linestyle=":", alpha=0.15)

    _apply_axis_scale(ax, chart_spec.left_axis)
    if ax2 is not None:
        _apply_axis_scale(ax2, chart_spec.right_axis)

    # 秒 → mm:ss 表示
    if getattr(chart_spec.left_axis, "formatter", None) == "mmss":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: _format_mmss(x)))
    if ax2 is not None and getattr(chart_spec.right_axis, "formatter", None) == "mmss":
        ax2.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, pos: _format_mmss(x)))

    # ---- 実データ系列 ----
    colors = getattr(
        chart_spec,
        "palette",
        ("#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b"),
    )

    plotted_last_points = []  # 注釈用
    for i, s in enumerate(chart_spec.series):
        y_col = s.col
        if y_col not in dff.columns:
            continue
        x = dff[chart_spec.date_col]
        y = pd.to_numeric(dff[y_col], errors="coerce")

        tgt_ax = ax2 if (ax2 is not None and s.axis == "right") else ax
        color = _pick_color(colors, i)

        tgt_ax.plot(
            x,
            y,
            label=s.label,
            linewidth=s.width if s.width else 2.2,
            linestyle=s.linestyle if s.linestyle else "-",
            marker=s.marker if s.marker else "o",
            markersize=s.marker_size if s.marker_size else 4.8,
            color=color,
        )

        # 最新点
        if show_latest_annotation and getattr(chart_spec, "latest_annotation", False):
            try:
                valid = y.dropna()
                if len(valid) > 0:
                    last_idx = valid.index[-1]
                    plotted_last_points.append((tgt_ax, x.loc[last_idx], y.loc[last_idx], s, color))
            except Exception:
                pass

    # ---- ROADMAP（low/mid/high）を点線で重ねる（指定がある時だけ）----
    if roadmap and getattr(chart_spec, "roadmap_keys", None):
        # roadmap_keys: (low_col, mid_col, high_col)
        low_key, mid_key, high_key = chart_spec.roadmap_keys
        # 月を日付に展開（該当月の1日）
        xs = []
        low_vals, mid_vals, high_vals = [], [], []
        for ym, row in roadmap.items():
            try:
                dt = pd.to_datetime(f"{ym}-01", errors="coerce")
            except Exception:
                dt = pd.NaT
            if pd.isna(dt):
                continue
            xs.append(dt)
            low_vals.append(row.get(low_key))
            mid_vals.append(row.get(mid_key))
            high_vals.append(row.get(high_key))

        # どっちの軸に出すか（基本は左。右軸が指定されているなら series 側に合わせる）
        tgt = ax
        if ax2 is not None and getattr(chart_spec, "roadmap_axis", "left") == "right":
            tgt = ax2

        def _plot_rm(vals, style: str, alpha: float):
            v = pd.to_numeric(pd.Series(vals), errors="coerce")
            tgt.plot(xs, v, linestyle=style, linewidth=1.2, alpha=alpha)

        # low/mid/high を薄い点線で
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

    # 最新値注釈
    if plotted_last_points:
        for tgt_ax, x0, y0, s, color in plotted_last_points:
            try:
                # mm:ss formatter の時だけ mm:ss、そうでなければ小数表示
                formatter_name = tgt_ax.yaxis.get_major_formatter().__class__.__name__
                if formatter_name == "FuncFormatter" and getattr(s, "formatter", None) == "mmss":
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
