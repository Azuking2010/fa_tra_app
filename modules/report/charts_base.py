# modules/report/charts_base.py
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

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


# =========================================================
# 日本語フォント：assets/fonts 配下を自動探索して適用
# =========================================================
@dataclass
class JpFontResult:
    applied: bool
    font_name: str = ""
    font_path: str = ""
    error: str = ""


def _project_root_from_here(this_file: str) -> Path:
    # .../modules/report/charts_base.py -> project root は parents[2] 想定
    # charts_base.py (report) -> modules -> project_root
    p = Path(this_file).resolve()
    return p.parents[2]


def _find_font_files(root: Path) -> list[Path]:
    if not root.exists():
        return []
    exts = {".ttf", ".otf", ".ttc"}
    files: list[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in exts:
            files.append(p)
    return files


def apply_jp_font_auto() -> JpFontResult:
    """
    assets/fonts 配下を再帰検索してフォントを見つけ、Matplotlibに登録＆適用。
    失敗しても例外は投げず、グラフは描画できる（ただし日本語は□になる）。
    """
    require_mpl()

    try:
        project_root = _project_root_from_here(__file__)
        fonts_root = project_root / "assets" / "fonts"
        candidates = _find_font_files(fonts_root)

        if not candidates:
            return JpFontResult(
                applied=False,
                error=f"no font files found under: {fonts_root}",
            )

        # Noto Sans JP 系を優先
        def score(path: Path) -> int:
            name = path.name.lower()
            s = 0
            if "noto" in name:
                s += 10
            if "sans" in name:
                s += 5
            if "jp" in name or "japanese" in name:
                s += 20
            if "variable" in name:
                s += 2
            if "bold" in name:
                s += 1
            return s

        candidates.sort(key=score, reverse=True)
        chosen = candidates[0]

        # フォント登録
        fm.fontManager.addfont(str(chosen))
        fp = fm.FontProperties(fname=str(chosen))
        font_name = fp.get_name()

        # グローバル既定フォントに反映
        plt.rcParams["font.family"] = font_name
        plt.rcParams["axes.unicode_minus"] = False  # マイナス記号の文字化け回避

        return JpFontResult(applied=True, font_name=font_name, font_path=str(chosen))

    except Exception as e:
        return JpFontResult(applied=False, error=str(e))


# =========================================================
# 共通：軸・見た目ユーティリティ
# =========================================================
def setup_ax(ax, title: str, ylabel_left: str | None = None, ylabel_right: str | None = None):
    require_mpl()
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    if ylabel_left:
        ax.set_ylabel(ylabel_left)
    if ylabel_right and hasattr(ax, "right_ax"):
        ax.right_ax.set_ylabel(ylabel_right)


def build_period_text(df, date_col: str = "date") -> str:
    """
    df[date] の min/max から "YYYY-MM-DD ～ YYYY-MM-DD" を作る
    """
    if df is None or len(df) == 0 or date_col not in df.columns:
        return ""
    try:
        dmin = df[date_col].min()
        dmax = df[date_col].max()
        # pandas Timestamp / datetime / date を想定
        smin = str(dmin)[:10]
        smax = str(dmax)[:10]
        if smin == smax:
            return smin
        return f"{smin} ～ {smax}"
    except Exception:
        return ""


def annotate_latest(ax, x, y, text: str, dx: int = 6, dy: int = 0):
    """
    最新点の右側に注釈を付ける（折線グラフ共通）
    """
    require_mpl()
    if x is None or y is None:
        return
    try:
        ax.annotate(
            text,
            (x, y),
            textcoords="offset points",
            xytext=(dx, dy),
            ha="left",
            va="center",
            fontsize=9,
        )
    except Exception:
        pass


# =========================================================
# 秒→mm:ss 表記（表示だけを変える：データは秒のまま）
# =========================================================
def seconds_to_mmss(sec: float | int) -> str:
    try:
        s = int(round(float(sec)))
    except Exception:
        return ""
    m = s // 60
    r = s % 60
    return f"{m}:{r:02d}"


def apply_mmss_yaxis(ax):
    """
    Y軸の目盛り表示を mm:ss にする（値は秒のまま）
    """
    require_mpl()
    if FuncFormatter is None:
        return

    def _fmt(v, _pos):
        return seconds_to_mmss(v)

    ax.yaxis.set_major_formatter(FuncFormatter(_fmt))
