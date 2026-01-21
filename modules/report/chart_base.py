# modules/report/chart_base.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple, Dict

import pandas as pd

_MPL_READY = False


def require_mpl() -> None:
    """
    matplotlib を遅延importし、Noto Sans JP を必ず登録する。
    Streamlit Cloud（Linux）でも文字化けを再発させないための唯一の入口。
    """
    global _MPL_READY
    if _MPL_READY:
        return

    import matplotlib
    import matplotlib.pyplot as plt  # noqa: F401
    from matplotlib import font_manager, rcParams

    # このファイル: .../fa_tra_app/modules/report/chart_base.py
    # assets:     .../fa_tra_app/assets/fonts/Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf
    app_root = Path(__file__).resolve().parents[2]
    font_path = app_root / "assets" / "fonts" / "Noto_Sans_JP" / "NotoSansJP-VariableFont_wght.ttf"

    if font_path.exists():
        try:
            font_manager.fontManager.addfont(str(font_path))
            rcParams["font.family"] = ["Noto Sans JP", "DejaVu Sans"]
        except Exception:
            # 最悪でも豆腐化しないように一般フォントへフォールバック
            rcParams["font.family"] = ["DejaVu Sans"]
    else:
        rcParams["font.family"] = ["DejaVu Sans"]

    rcParams["axes.unicode_minus"] = False
    _MPL_READY = True


def _sec_to_mmss(sec: float) -> str:
    try:
        s = int(round(float(sec)))
    except Exception:
        return ""
    m = s // 60
    r = s % 60
    return f"{m}:{r:02d}"


def _format_value(fmt: str, v: float) -> str:
    if fmt == "mmss":
        return _sec_to_mmss(v)
    if fmt == "sec_float":
        # 50m用
        return f"{v:.2f}".rstrip("0").rstrip(".")
    if fmt == "int":
        try:
            return str(int(round(v)))
        except Exception:
            return ""
    return f"{v:g}"


def _apply_axis_ticks(ax, vmin: float, vmax: float, major: float, minor: Optional[float], fmt: str):
    from matplotlib.ticker import MultipleLocator, FuncFormatter

    # locator
    ax.yaxis.set_major_locator(MultipleLocator(major))
    if minor is not None:
        ax.yaxis.set_minor_locator(MultipleLocator(minor))

    # formatter
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: _format_value(fmt, x)))

    # limits
    ax.set_ylim(vmin, vmax)

    # grid
    ax.grid(True, which="major", axis="y", alpha=0.25)
    if minor is not None:
        ax.grid(True, which="minor", axis="y", alpha=0.12)


def _safe_series(df: pd.DataFrame, col: str):
    if col not in df.columns:
        return None
    s = pd.to_numeric(df[col], errors="coerce")
    if s.notna().sum() == 0:
        return None
    return s


@dataclass(frozen=True)
class BuiltAxes:
    fig: object
    ax_left: object
    ax_right: Optional[object]


def build_line_chart(
    df: pd.DataFrame,
    spec,
    period_text: Optional[str] = None,
    roadmap_df: Optional[pd.DataFrame] = None,
) -> object:
    """
    spec: chart_config.ChartSpec
    df: date_col + series cols
    roadmap_df: ROADMAP(目標帯)のdf（同じdate_colで揃える）
    """
    require_mpl()
    import matplotlib.pyplot as plt

    if df is None or df.empty:
        fig = plt.figure(figsize=(10, 3.4))
        plt.text(0.5, 0.5, "No data", ha="center", va="center")
        plt.axis("off")
        return fig

    # date col
    date_col = spec.date_col
    if date_col not in df.columns:
        # 最低限のフォールバック
        df = df.copy()
        df[date_col] = range(len(df))

    x = pd.to_datetime(df[date_col], errors="coerce")
    if x.isna().all():
        # 文字列/数値ならそのまま
        x = df[date_col]

    fig = plt.figure(figsize=(10, 3.6))
    ax = fig.add_subplot(111)

    # Title
    title = spec.title
    if period_text:
        ax.set_title(f"{title}\n{period_text}", fontsize=11)
    else:
        ax.set_title(title, fontsize=11)

    # Left axis
    ax.set_ylabel(spec.left_axis.label)
    _apply_axis_ticks(
        ax,
        spec.left_axis.vmin,
        spec.left_axis.vmax,
        spec.left_axis.major_step,
        spec.left_axis.minor_step,
        spec.left_axis.value_format,
    )

    # plot left lines
    from .chart_config import PALETTE_RGB01, darken, lighten

    for i, col in enumerate(spec.left_cols):
        s = _safe_series(df, col)
        if s is None:
            continue
        color = PALETTE_RGB01[spec.palette_index_left[i % len(spec.palette_index_left)]]
        ax.plot(x, s, color=color, linewidth=2.4, marker="o", markersize=5.0, label=spec.left_labels[i])

        # ROADMAP (low/mid/high)
        if spec.roadmap and spec.roadmap.enabled and spec.roadmap_cols and col in spec.roadmap_cols:
            if roadmap_df is not None and not roadmap_df.empty:
                low_c, mid_c, high_c = spec.roadmap_cols[col]
                for kind, cfunc, label_suffix in [
                    ("low", darken, "目標(低)"),
                    ("mid", lambda c: c, "目標(中)"),
                    ("high", lighten, "目標(高)"),
                ]:
                    rcol = {"low": low_c, "mid": mid_c, "high": high_c}[kind]
                    rs = _safe_series(roadmap_df, rcol)
                    if rs is None:
                        continue
                    rx = pd.to_datetime(roadmap_df[date_col], errors="coerce")
                    if rx.isna().all():
                        rx = roadmap_df[date_col]
                    ax.plot(
                        rx,
                        rs,
                        color=cfunc(color),
                        linewidth=spec.roadmap.linewidth,
                        linestyle=spec.roadmap.linestyle,
                        alpha=spec.roadmap.alpha,
                        label=f"{spec.left_labels[i]} {label_suffix}",
                    )

    # Right axis
    ax2 = None
    if spec.right_axis is not None and len(spec.right_cols) > 0:
        ax2 = ax.twinx()
        ax2.set_ylabel(spec.right_axis.label)
        _apply_axis_ticks(
            ax2,
            spec.right_axis.vmin,
            spec.right_axis.vmax,
            spec.right_axis.major_step,
            spec.right_axis.minor_step,
            spec.right_axis.value_format,
        )

        for i, col in enumerate(spec.right_cols):
            s = _safe_series(df, col)
            if s is None:
                continue
            color = PALETTE_RGB01[spec.palette_index_right[i % len(spec.palette_index_right)]]
            ax2.plot(x, s, color=color, linewidth=2.4, marker="o", markersize=5.0, label=spec.right_labels[i])

            # ROADMAP
            if spec.roadmap and spec.roadmap.enabled and spec.roadmap_cols and col in spec.roadmap_cols:
                if roadmap_df is not None and not roadmap_df.empty:
                    low_c, mid_c, high_c = spec.roadmap_cols[col]
                    for kind, cfunc, label_suffix in [
                        ("low", darken, "目標(低)"),
                        ("mid", lambda c: c, "目標(中)"),
                        ("high", lighten, "目標(高)"),
                    ]:
                        rcol = {"low": low_c, "mid": mid_c, "high": high_c}[kind]
                        rs = _safe_series(roadmap_df, rcol)
                        if rs is None:
                            continue
                        rx = pd.to_datetime(roadmap_df[date_col], errors="coerce")
                        if rx.isna().all():
                            rx = roadmap_df[date_col]
                        ax2.plot(
                            rx,
                            rs,
                            color=cfunc(color),
                            linewidth=spec.roadmap.linewidth,
                            linestyle=spec.roadmap.linestyle,
                            alpha=spec.roadmap.alpha,
                            label=f"{spec.right_labels[i]} {label_suffix}",
                        )

    # Legend (merge)
    handles1, labels1 = ax.get_legend_handles_labels()
    if ax2 is not None:
        handles2, labels2 = ax2.get_legend_handles_labels()
        handles = handles1 + handles2
        labels = labels1 + labels2
    else:
        handles, labels = handles1, labels1

    if handles:
        ax.legend(handles, labels, loc="upper right", fontsize=9, framealpha=0.85)

    fig.tight_layout()
    return fig
