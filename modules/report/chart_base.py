# modules/report/chart_base.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import pandas as pd


def require_mpl():
    """
    Matplotlib を遅延importする（Streamlit Cloudでも安全に動くようにする）。
    """
    import matplotlib
    matplotlib.use("Agg")  # サーバー環境向け
    import matplotlib.pyplot as plt  # noqa
    return plt


def apply_jp_font():
    """
    assets/fonts/Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf を優先して設定。
    """
    plt = require_mpl()
    import matplotlib as mpl
    from matplotlib import font_manager

    # repo root 推定： modules/report/chart_base.py -> modules/report -> modules -> root
    root = Path(__file__).resolve().parents[2]
    font_path = root / "assets" / "fonts" / "Noto_Sans_JP" / "NotoSansJP-VariableFont_wght.ttf"

    if font_path.exists():
        font_manager.fontManager.addfont(str(font_path))
        prop = font_manager.FontProperties(fname=str(font_path))
        mpl.rcParams["font.family"] = prop.get_name()
    else:
        # フォールバック（環境依存）
        mpl.rcParams["font.family"] = ["Noto Sans CJK JP", "Noto Sans JP", "IPAexGothic", "sans-serif"]

    mpl.rcParams["axes.unicode_minus"] = False
    return plt


def sec_to_mmss(sec: float) -> str:
    try:
        s = int(round(float(sec)))
    except Exception:
        return ""
    m = s // 60
    r = s % 60
    return f"{m}:{r:02d}"


def _set_ticks(ax, ymin: float, ymax: float, step: float):
    import numpy as np
    if step <= 0:
        return
    lo, hi = float(ymin), float(ymax)
    # 反転でも ticksは min->max の範囲で作る
    mn, mx = (min(lo, hi), max(lo, hi))
    ticks = np.arange(mn, mx + (step * 0.5), step)
    ax.set_yticks(ticks)


def _apply_axis_config(ax, axis_cfg):
    ax.set_ylabel(axis_cfg.label)
    ax.set_ylim(axis_cfg.ymin, axis_cfg.ymax)
    _set_ticks(ax, axis_cfg.ymin, axis_cfg.ymax, axis_cfg.major_step)

    if axis_cfg.formatter == "sec_to_mmss":
        ax.set_yticklabels([sec_to_mmss(t) for t in ax.get_yticks()])

    if axis_cfg.invert:
        ax.invert_yaxis()


def _ensure_dt(df: pd.DataFrame, date_col: str) -> pd.DataFrame:
    out = df.copy()
    if date_col not in out.columns:
        out[date_col] = pd.NaT
    out["_dt"] = pd.to_datetime(out[date_col], errors="coerce")
    out = out[out["_dt"].notna()].sort_values("_dt").reset_index(drop=True)
    return out


def _ym_from_dt(ts: pd.Timestamp) -> str:
    return f"{ts.year:04d}-{ts.month:02d}"


def build_line_chart(
    df: pd.DataFrame,
    chart_spec,
    period_text: str = "",
    roadmap: Optional[Dict[str, Dict[str, Any]]] = None,
):
    """
    chart_spec: ChartSpec（chart_config.py の定義）
    roadmap: ym -> {col_low/col_mid/col_high: value, ...}
    """
    plt = apply_jp_font()

    # 前処理
    dff = _ensure_dt(df, chart_spec.date_col)

    fig = plt.figure(figsize=(10.8, 4.6))
    ax = fig.add_subplot(111)

    ax2 = ax.twinx() if chart_spec.right_axis else None

    # 軸設定
    _apply_axis_config(ax, chart_spec.left_axis)
    if ax2 is not None:
        _apply_axis_config(ax2, chart_spec.right_axis)

    # グリッド（見やすさ）
    ax.grid(True, axis="y", linestyle=":", linewidth=0.8, alpha=0.6)

    # タイトル
    title = chart_spec.title
    if period_text:
        title = f"{title}\n{period_text}"
    ax.set_title(title)

    # プロット
    from .chart_config import get_base_color, get_roadmap_color  # local import to avoid cycles

    x = dff["_dt"]

    for s in chart_spec.series:
        if s.col not in dff.columns:
            # 欠けても落とさない
            continue
        y = pd.to_numeric(dff[s.col], errors="coerce")
        target_ax = ax if s.axis == "left" else ax2
        if target_ax is None:
            target_ax = ax
        color = get_base_color(s.color_index)
        target_ax.plot(
            x,
            y,
            label=s.label,
            linewidth=s.linewidth,
            marker=s.marker,
            color=color,
        )

    # ROADMAP（low/mid/high を点線で重ねる）
    if roadmap and chart_spec.roadmap:
        for rm in chart_spec.roadmap:
            # roadmap col: {rm.col}_low/mid/high を参照
            low_key = f"{rm.col}_low"
            mid_key = f"{rm.col}_mid"
            high_key = f"{rm.col}_high"

            # xごとに ym を作って roadmap から値を拾う
            y_low = []
            y_mid = []
            y_high = []
            for ts in x:
                ym = _ym_from_dt(pd.Timestamp(ts))
                row = roadmap.get(ym, {}) if roadmap else {}
                y_low.append(row.get(low_key))
                y_mid.append(row.get(mid_key))
                y_high.append(row.get(high_key))

            target_ax = ax if rm.axis == "left" else ax2
            if target_ax is None:
                target_ax = ax

            # ベース色は「その系列が存在する場合は同じ color_index を使う」方針
            # → rm.col と一致する series を探す
            color_index = None
            for s in chart_spec.series:
                if s.col == rm.col:
                    color_index = s.color_index
                    break
            if color_index is None:
                color_index = 1

            c_low = get_roadmap_color(color_index, "low", rm.low_factor, rm.mid_factor, rm.high_factor)
            c_mid = get_roadmap_color(color_index, "mid", rm.low_factor, rm.mid_factor, rm.high_factor)
            c_high = get_roadmap_color(color_index, "high", rm.low_factor, rm.mid_factor, rm.high_factor)

            # “普通(mid)”は基本色で細い点線、lowは暗め、highは明るめ
            target_ax.plot(x, y_low, linestyle=rm.style, linewidth=rm.linewidth, alpha=rm.alpha, color=c_low)
            target_ax.plot(x, y_mid, linestyle=rm.style, linewidth=rm.linewidth, alpha=rm.alpha, color=c_mid)
            target_ax.plot(x, y_high, linestyle=rm.style, linewidth=rm.linewidth, alpha=rm.alpha, color=c_high)

    # 凡例（左右の両方をまとめる）
    handles = []
    labels = []
    h1, l1 = ax.get_legend_handles_labels()
    handles += h1
    labels += l1
    if ax2 is not None:
        h2, l2 = ax2.get_legend_handles_labels()
        handles += h2
        labels += l2

    if handles:
        ax.legend(handles, labels, loc="upper left", frameon=True)

    fig.tight_layout()
    return fig
