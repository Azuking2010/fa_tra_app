# modules/report/chart_base.py
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple, Any, List

try:
    import matplotlib.pyplot as plt
    from matplotlib import font_manager
    from matplotlib.ticker import MultipleLocator, FuncFormatter
    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False

from .chart_config import AxisSpec, SeriesSpec, ChartSpec


def require_mpl():
    if not HAS_MPL:
        raise ModuleNotFoundError("matplotlib is required for report charts, but it is not installed.")


# =========================================
# Font (MUST run before any figure is created)
# =========================================
_FONT_INITIALIZED = False

def init_japanese_font(font_dir: Optional[str | Path] = None):
    """
    Ensures Japanese font is available both locally and on Streamlit Cloud.
    - If font_dir is None, we use repo-relative: assets/fonts/Noto_Sans_JP
    """
    global _FONT_INITIALIZED
    if _FONT_INITIALIZED:
        return
    require_mpl()

    if font_dir is None:
        # modules/report/chart_base.py -> project_root/assets/fonts/Noto_Sans_JP
        project_root = Path(__file__).resolve().parents[2]
        font_dir = project_root / "assets" / "fonts" / "Noto_Sans_JP"

    font_dir = Path(font_dir)
    # Pick a .ttf
    candidates = []
    if font_dir.exists():
        candidates += list(font_dir.glob("*.ttf"))
        candidates += list(font_dir.glob("**/*.ttf"))

    if candidates:
        # Add all fonts to be safe (VariableFont included)
        for fp in candidates:
            try:
                font_manager.fontManager.addfont(str(fp))
            except Exception:
                pass

        # Prefer Noto Sans JP family name
        plt.rcParams["font.family"] = "Noto Sans JP"
        plt.rcParams["axes.unicode_minus"] = False

    _FONT_INITIALIZED = True


# =========================================
# Formatters
# =========================================
def sec_to_mmss(sec: float) -> str:
    sec_int = int(round(sec))
    m = sec_int // 60
    s = sec_int % 60
    return f"{m}:{s:02d}"


def make_mmss_formatter():
    return FuncFormatter(lambda x, pos: sec_to_mmss(x))


# =========================================
# Base chart builder
# =========================================
def build_line_chart(
    df,
    spec: ChartSpec,
    period_text: Optional[str] = None,
    show_latest_annotation: bool = True,
):
    """
    Pure chart builder:
    - reads spec
    - draws left axis series and optional right axis series
    - applies axis range, ticks, inversion, labels, title (with period)
    """
    require_mpl()
    init_japanese_font()  # <<== ここが重要：分割しても毎回必ず先に当たる

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = None

    x = df[spec.x]

    # left axis
    if spec.left_series:
        for s in spec.left_series:
            if s.key in df.columns:
                ax1.plot(
                    x, df[s.key],
                    label=s.label,
                    color=s.color,
                    linewidth=s.linewidth,
                    marker=s.marker,
                )

    # right axis
    if spec.right_axis and spec.right_series:
        ax2 = ax1.twinx()
        for s in spec.right_series:
            if s.key in df.columns:
                ax2.plot(
                    x, df[s.key],
                    label=s.label,
                    color=s.color,
                    linewidth=s.linewidth,
                    marker=s.marker,
                )

    # title
    title = spec.title
    if period_text:
        title = f"{title}\n{period_text}"
    ax1.set_title(title)

    # axis labels
    if spec.left_series and len(spec.left_series) == 1:
        ax1.set_ylabel(spec.left_series[0].label)
    else:
        ax1.set_ylabel("")

    if ax2 is not None:
        if spec.right_series and len(spec.right_series) == 1:
            ax2.set_ylabel(spec.right_series[0].label)
        else:
            ax2.set_ylabel("")

    # grid
    ax1.grid(True, axis="y", alpha=0.3)

    # ranges & ticks (left)
    apply_axis_spec(ax1, spec.left_axis, mmss=(spec.y_format == "mmss"))

    # ranges & ticks (right)
    if ax2 is not None and spec.right_axis is not None:
        apply_axis_spec(ax2, spec.right_axis, mmss=False)

    # legends
    ax1.legend(loc="upper left")
    if ax2 is not None:
        ax2.legend(loc="upper right", fontsize=8)

    # latest annotation (last non-null)
    if show_latest_annotation:
        annotate_latest(ax1, df, spec.left_series, fmt=("mmss" if spec.y_format == "mmss" else None))
        if ax2 is not None:
            annotate_latest(ax2, df, spec.right_series, fmt=None)

    return fig


def apply_axis_spec(ax, axis_spec: AxisSpec, mmss: bool = False):
    ax.set_ylim(axis_spec.ymin, axis_spec.ymax)

    # invert means "smaller is better": make y-axis reversed
    # (Note: if ymin>ymax already, matplotlib is reversed; but we keep it explicit)
    if axis_spec.invert and axis_spec.ymin < axis_spec.ymax:
        ax.invert_yaxis()

    # ticks
    ax.yaxis.set_major_locator(MultipleLocator(axis_spec.major))
    if axis_spec.minor:
        ax.yaxis.set_minor_locator(MultipleLocator(axis_spec.minor))

    # mm:ss formatter (for 1500/3000)
    if mmss:
        ax.yaxis.set_major_formatter(make_mmss_formatter())


def annotate_latest(ax, df, series_list: Optional[List[SeriesSpec]], fmt: Optional[str] = None):
    if not series_list:
        return
    x = df["date"]
    for s in series_list:
        if s.key not in df.columns:
            continue
        y = df[s.key]
        # find last valid
        last_idx = y.last_valid_index()
        if last_idx is None:
            continue
        x_last = df.loc[last_idx, "date"]
        y_last = df.loc[last_idx, s.key]

        if fmt == "mmss":
            text = sec_to_mmss(float(y_last))
        else:
            # numeric
            try:
                text = f"{float(y_last):.1f}"
            except Exception:
                text = str(y_last)

        ax.annotate(
            text,
            xy=(x_last, y_last),
            xytext=(6, 0),
            textcoords="offset points",
            ha="left",
            va="center",
            fontsize=9,
        )
