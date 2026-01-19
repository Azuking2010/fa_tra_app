# modules/report/charts_base.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Iterable, Any

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
    from matplotlib import font_manager as fm
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:
    plt = None
    fm = None
    FuncFormatter = None
    HAS_MPL = False


def require_mpl():
    if not HAS_MPL:
        raise ModuleNotFoundError(
            "matplotlib is required for report charts, but it is not installed."
        )


@dataclass
class ChartStyle:
    title_fontsize: int = 12
    label_fontsize: int = 10
    tick_fontsize: int = 9
    legend_fontsize: int = 9


DEFAULT_STYLE = ChartStyle()


def apply_jp_font(noto_font_path: Optional[str] = None):
    """
    日本語フォントを matplotlib に適用する。
    noto_font_path が None の場合は matplotlib の既定フォントを使う（日本語が□になる可能性あり）
    """
    require_mpl()
    if not noto_font_path:
        return

    try:
        fp = fm.FontProperties(fname=noto_font_path)
        # 全体のデフォルトに適用
        plt.rcParams["font.family"] = fp.get_name()
        # 記号マイナスが豆腐になる対策
        plt.rcParams["axes.unicode_minus"] = False
    except Exception:
        # フォント適用に失敗しても、描画は止めない（□になるだけ）
        pass


def make_period_str(dates) -> str:
    """
    dates: pandas Series / list など。date型でも文字列でもOK。
    """
    if dates is None:
        return ""
    try:
        dmin = min(dates)
        dmax = max(dates)
        return f"{dmin} 〜 {dmax}"
    except Exception:
        return ""


def setup_ax(ax, title: str, ylabel_left: str | None = None, ylabel_right: str | None = None, style: ChartStyle = DEFAULT_STYLE):
    ax.set_title(title, fontsize=style.title_fontsize)
    ax.grid(True, axis="y", alpha=0.25)
    if ylabel_left:
        ax.set_ylabel(ylabel_left, fontsize=style.label_fontsize)
    if ylabel_right and hasattr(ax, "right_ax") and ax.right_ax is not None:
        ax.right_ax.set_ylabel(ylabel_right, fontsize=style.label_fontsize)

    # tick size
    for t in ax.get_xticklabels():
        t.set_fontsize(style.tick_fontsize)
    for t in ax.get_yticklabels():
        t.set_fontsize(style.tick_fontsize)
    if hasattr(ax, "right_ax") and ax.right_ax is not None:
        for t in ax.right_ax.get_yticklabels():
            t.set_fontsize(style.tick_fontsize)


def to_seconds_series(values, mmss: bool) -> list[float | None]:
    """
    保存形式が混在しても「秒」に正規化するための関数。
    - mmss=False の場合はそのままfloat化
    - mmss=True の場合も内部は秒で扱う（表示だけ mm:ss）
    """
    out: list[float | None] = []
    for v in values:
        if v is None:
            out.append(None)
            continue
        try:
            fv = float(v)
        except Exception:
            out.append(None)
            continue

        # ここが肝：
        # 1500/3000 は「秒」で入ってくる想定だが、
        # もし 0.0x のような値が混ざった場合（分/時換算など）を吸収する余地を残す。
        # ※ 現状の運用で "秒" に揃っているなら、そのまま通る。
        out.append(fv)
    return out


def fmt_mmss_from_seconds(sec: float) -> str:
    if sec is None:
        return ""
    try:
        s = int(round(float(sec)))
    except Exception:
        return ""
    m = s // 60
    r = s % 60
    return f"{m}:{r:02d}"


def make_mmss_formatter():
    """
    y軸用 mm:ss フォーマッタ
    """
    require_mpl()
    return FuncFormatter(lambda x, pos: fmt_mmss_from_seconds(x))


def annotate_latest(ax, x, y, text: str, dx: float = 0, dy: float = 0):
    """
    最新点の注釈。座標はデータ座標。
    """
    try:
        ax.annotate(
            text,
            (x, y),
            textcoords="offset points",
            xytext=(6 + dx, 0 + dy),
            ha="left",
            va="center",
            fontsize=9,
        )
    except Exception:
        pass
