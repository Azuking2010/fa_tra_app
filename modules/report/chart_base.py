# modules/report/chart_base.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Sequence, List, Tuple, Union

import math

# matplotlib は重いので遅延importしたい
_MPL_READY = False


def require_mpl():
    global _MPL_READY
    if _MPL_READY:
        return
    import matplotlib  # noqa
    import matplotlib.pyplot as plt  # noqa
    import matplotlib.ticker as mticker  # noqa
    _MPL_READY = True


def init_japanese_font():
    """
    ✅ 重要：
    - Streamlit Cloud / ローカル どちらでも assets/fonts を相対で拾う
    - 毎回呼んでも問題ないように冪等
    """
    require_mpl()
    import matplotlib as mpl
    from matplotlib import font_manager

    root = Path(__file__).resolve().parents[2]  # .../fa_tra_app
    font_dir = root / "assets" / "fonts" / "Noto_Sans_JP"
    font_path = font_dir / "NotoSansJP-VariableFont_wght.ttf"

    if font_path.exists():
        try:
            font_manager.fontManager.addfont(str(font_path))
            prop = font_manager.FontProperties(fname=str(font_path))
            mpl.rcParams["font.family"] = prop.get_name()
        except Exception:
            # フォント登録に失敗しても落とさない（英字で表示継続）
            pass

    # マイナス記号などの文字化け対策
    mpl.rcParams["axes.unicode_minus"] = False


# ---------- Dataclasses ----------

@dataclass(frozen=True)
class AxisSpec:
    ymin: float
    ymax: float
    major_step: Optional[float] = None
    minor_step: Optional[float] = None
    label: Optional[str] = None


@dataclass(frozen=True)
class SeriesSpec:
    col: str
    label: str
    color: str
    lw: float = 2.4
    marker: str = "o"


@dataclass(frozen=True)
class RoadmapBandSpec:
    """
    low/mid/high を "薄い点線" で重ねる用途
    """
    col_low: str
    col_mid: str
    col_high: str
    base_color: str
    lw: float = 1.2
    ls: str = (0, (2, 2))  # dotted


@dataclass(frozen=True)
class ChartSpec:
    title: str
    left_axis: AxisSpec
    left_series: Sequence[SeriesSpec]

    right_axis: Optional[AxisSpec] = None
    right_series: Optional[Sequence[SeriesSpec]] = None

    y_format: str = "num"  # "num" or "mmss"
    roadmap: Optional[RoadmapBandSpec] = None


# ---------- Helpers ----------

def _parse_mmss_to_seconds(v: Union[str, float, int]) -> Optional[float]:
    """
    入力値が
      - "4:54" のような mm:ss
      - 数値 (minutes) または (seconds)
    のどちらでも秒に正規化して返す。
    """
    if v is None:
        return None

    if isinstance(v, str):
        s = v.strip()
        if not s:
            return None
        if ":" in s:
            parts = s.split(":")
            if len(parts) != 2:
                return None
            try:
                m = int(parts[0])
                sec = float(parts[1])
                return m * 60.0 + sec
            except ValueError:
                return None
        # ":"無し文字列は数値扱いを試す
        try:
            v = float(s)
        except ValueError:
            return None

    # 数値の場合
    try:
        x = float(v)
    except Exception:
        return None

    # ヒューリスティック：
    # 50mは 5〜10くらい→秒
    # 1500mが 4〜6 みたいな値なら "分" で入ってる可能性が高い→秒へ
    if 0 < x < 60:
        # 4.9 などが来たら minutes とみなす（1500m/3000m用）
        # ただし 50m(8.2) みたいなのは seconds の可能性が高いので、
        # 10以下は seconds 優先
        if x <= 10.5:
            return x
        return x * 60.0

    return x


def _coerce_series_seconds(df, cols: Sequence[str]) -> None:
    """
    df の指定列を mm:ss → 秒 float に正規化（破壊的）
    """
    for c in cols:
        if c not in df.columns:
            continue
        df[c] = df[c].apply(_parse_mmss_to_seconds)


def _format_seconds_mmss(x: float) -> str:
    if x is None or (isinstance(x, float) and (math.isnan(x))):
        return ""
    x = float(x)
    m = int(x // 60)
    s = int(round(x - 60 * m))
    return f"{m}:{s:02d}"


def apply_axis_spec(ax, axis_spec: AxisSpec, y_format: str = "num"):
    require_mpl()
    import matplotlib.ticker as mticker

    ax.set_ylim(axis_spec.ymin, axis_spec.ymax)

    if axis_spec.label:
        ax.set_ylabel(axis_spec.label)

    if axis_spec.major_step:
        ax.yaxis.set_major_locator(mticker.MultipleLocator(axis_spec.major_step))
    if axis_spec.minor_step:
        ax.yaxis.set_minor_locator(mticker.MultipleLocator(axis_spec.minor_step))
        ax.grid(which="minor", alpha=0.15)
    ax.grid(which="major", alpha=0.25)

    if y_format == "mmss":
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, pos: _format_seconds_mmss(v)))


def annotate_latest(ax, df, series_list: Sequence[SeriesSpec], y_format: str = "num"):
    """
    最終値（最後の非null）を右端に注釈
    """
    for s in series_list:
        if s.col not in df.columns:
            continue
        sub = df[["date", s.col]].dropna()
        if sub.empty:
            continue
        last = sub.iloc[-1]
        y = float(last[s.col])
        txt = _format_seconds_mmss(y) if y_format == "mmss" else f"{y:g}"
        ax.annotate(
            txt,
            xy=(last["date"], y),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )


# ---------- Main builder ----------

def build_line_chart(
    df,
    spec: ChartSpec,
    period_text: Optional[str] = None,
    show_latest_annotation: bool = True,
):
    """
    - specに従って折れ線グラフを生成
    - 右軸も対応
    - mm:ss は内部を「秒」で統一して表示
    """
    require_mpl()
    init_japanese_font()

    import matplotlib.pyplot as plt

    # mm:ss系は df を秒に正規化
    if spec.y_format == "mmss":
        cols = [s.col for s in spec.left_series]
        if spec.right_series:
            cols += [s.col for s in spec.right_series]
        _coerce_series_seconds(df, cols)

    fig, ax1 = plt.subplots(figsize=(9.5, 4.8))

    # title
    title = spec.title
    if period_text:
        title = f"{title}\n{period_text}"
    ax1.set_title(title)

    # left axis
    apply_axis_spec(ax1, spec.left_axis, y_format=spec.y_format)
    for s in spec.left_series:
        if s.col in df.columns:
            ax1.plot(df["date"], df[s.col], label=s.label, color=s.color, linewidth=s.lw, marker=s.marker)

    # right axis
    ax2 = None
    if spec.right_axis and spec.right_series:
        ax2 = ax1.twinx()
        apply_axis_spec(ax2, spec.right_axis, y_format="num")  # 右軸は基本num（必要なら拡張）
        for s in spec.right_series:
            if s.col in df.columns:
                ax2.plot(df["date"], df[s.col], label=s.label, color=s.color, linewidth=s.lw, marker=s.marker)

    # roadmap overlay (low/mid/high)
    if spec.roadmap is not None:
        rm = spec.roadmap
        for col, tone in [(rm.col_low, -0.18), (rm.col_mid, 0.0), (rm.col_high, +0.18)]:
            if col in df.columns:
                # tone は chart_config 側で色を作って渡す方が本当は綺麗だけど、
                # ここでは "base_color" をそのまま使う（見た目差は configで指定）
                ax1.plot(df["date"], df[col], color=rm.base_color, linewidth=rm.lw, linestyle=rm.ls, alpha=0.6)

    # legends
    ax1.legend(loc="upper left", fontsize=9)
    if ax2 is not None:
        ax2.legend(loc="upper right", fontsize=9)

    # latest annotation
    if show_latest_annotation:
        annotate_latest(ax1, df, spec.left_series, y_format=spec.y_format)
        if ax2 is not None:
            annotate_latest(ax2, df, spec.right_series, y_format="num")

    fig.tight_layout()
    return fig
