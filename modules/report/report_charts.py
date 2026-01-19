# modules/report/report_charts.py
from __future__ import annotations

from pathlib import Path

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
    from matplotlib import rcParams
    from matplotlib.ticker import FuncFormatter
    from matplotlib.font_manager import FontProperties, fontManager

    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False


# =========================================================
# フォント（日本語）対策
# =========================================================
_JP_FONT_PROP: FontProperties | None = None


def _project_root() -> Path:
    # .../modules/report/report_charts.py からプロジェクトルートへ
    return Path(__file__).resolve().parents[2]


def _find_jp_font_path() -> Path | None:
    """
    できるだけ「static の Regular」を優先する（variable は環境で効かないことがある）
    探索候補は複数用意して、見つかったらそれを使う。
    """
    root = _project_root()

    candidates = [
        # よくある配置（あなたのスクショの構成に寄せる）
        root / "assets" / "fonts" / "Noto_Sans_JP" / "static" / "NotoSansJP-Regular.ttf",
        root / "assets" / "fonts" / "NotoSansJP-Regular.ttf",
        # variable（最後の手段）
        root / "assets" / "fonts" / "Noto_Sans_JP" / "NotoSansJP-VariableFont_wght.ttf",
        root / "assets" / "fonts" / "NotoSansJP-VariableFont_wght.ttf",
    ]

    for p in candidates:
        if p.exists():
            return p
    return None


def _setup_japanese_font():
    """
    Matplotlib に日本語フォントを登録し、以後の描画で使えるようにする。
    タイトル/軸/凡例は FontProperties を明示で渡す（これが一番確実）。
    """
    global _JP_FONT_PROP
    if _JP_FONT_PROP is not None:
        return

    font_path = _find_jp_font_path()
    if font_path is None:
        # フォントが見つからない場合は諦める（英語のまま表示される）
        _JP_FONT_PROP = None
        return

    try:
        fontManager.addfont(str(font_path))
        _JP_FONT_PROP = FontProperties(fname=str(font_path))
        # rcParams も一応設定（効く環境では効く）
        rcParams["font.family"] = _JP_FONT_PROP.get_name()
        rcParams["axes.unicode_minus"] = False
    except Exception:
        _JP_FONT_PROP = None


def _require_mpl():
    if not HAS_MPL:
        raise ModuleNotFoundError(
            "matplotlib is required for report charts, but it is not installed."
        )
    _setup_japanese_font()


# =========================================================
# 共通ユーティリティ
# =========================================================
def _period_str(df) -> str | None:
    if df is None or df.empty or "date" not in df.columns:
        return None
    try:
        d0 = str(df["date"].iloc[0])
        d1 = str(df["date"].iloc[-1])
        if d0 and d1:
            return f"{d0} ～ {d1}"
    except Exception:
        pass
    return None


def _jp(s: str) -> dict:
    """
    Matplotlib に日本語文字列を渡すときに fontproperties を一緒に渡すためのヘルパ
    """
    if _JP_FONT_PROP is None:
        return {}
    return {"fontproperties": _JP_FONT_PROP}


def _setup_ax(ax, title: str, ylabel_left: str | None = None, ylabel_right: str | None = None, period: str | None = None):
    if period:
        title = f"{title}\n{period}"

    ax.set_title(title, **_jp(title))
    ax.grid(True, axis="y", alpha=0.3)

    if ylabel_left:
        ax.set_ylabel(ylabel_left, **_jp(ylabel_left))
    if ylabel_right:
        ax.right_ax.set_ylabel(ylabel_right, **_jp(ylabel_right))

    # tick label も日本語フォントが必要なケースがあるので一応当てる
    if _JP_FONT_PROP is not None:
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(_JP_FONT_PROP)


def _annotate_last(ax, x_list, y_list, text: str):
    """
    最新値の数値注釈（右端に）
    """
    try:
        if not x_list or not y_list:
            return
        x = x_list[-1]
        y = y_list[-1]
        ax.annotate(
            text,
            (x, y),
            textcoords="offset points",
            xytext=(6, 0),
            ha="left",
            va="center",
            fontsize=9,
            **_jp(text),
        )
    except Exception:
        return


def _sec_to_mmss(sec: float) -> str:
    try:
        if sec is None:
            return "—"
        s = float(sec)
        if s <= 0:
            return "—"
        m = int(s) // 60
        r = int(round(s)) % 60
        return f"{m}:{r:02d}"
    except Exception:
        return "—"


def _mmss_formatter(_x, y):
    # FuncFormatter 用
    try:
        y = float(y)
    except Exception:
        return ""
    return _sec_to_mmss(y)


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2  # util 用

    x = df["date"].tolist()

    y_h = df["height_cm"].tolist() if "height_cm" in df.columns else []
    y_w = df["weight_kg"].tolist() if "weight_kg" in df.columns else []
    y_b = df["bmi"].tolist() if "bmi" in df.columns else []

    ax1.plot(x, y_h, label="身長 (cm)")
    ax2.plot(x, y_w, label="体重 (kg)")
    if "bmi" in df.columns:
        ax2.plot(x, y_b, label="BMI", linestyle="--")

    _setup_ax(ax1, "フィジカル推移（身長・体重・BMI）", "身長 (cm)", "体重 (kg) / BMI", period=period)

    # 最新値注釈
    if y_h:
        _annotate_last(ax1, x, y_h, f"{y_h[-1]:.1f}cm")
    if y_w:
        _annotate_last(ax2, x, y_w, f"{y_w[-1]:.1f}kg")

    # 凡例（日本語フォントを明示）
    if _JP_FONT_PROP is not None:
        ax1.legend(loc="upper left", prop=_JP_FONT_PROP)
        ax2.legend(loc="upper right", prop=_JP_FONT_PROP)
    else:
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")

    return fig


# =========================================================
# P2: 走力（50m / 1500m / 3000m）
# =========================================================
def fig_run_metric(
    report,
    metric: str,
    title: str,
    show_roadmap: bool = True,
    mmss: bool = False,
):
    _require_mpl()

    df = report.portfolio
    period = _period_str(df)

    fig, ax = plt.subplots(figsize=(8, 4))

    x = df["date"].tolist()
    y = df[metric].tolist() if metric in df.columns else []

    ax.plot(x, y, marker="o")

    # タイトル（日本語化 + 期間表示）
    _setup_ax(ax, title, period=period)

    # 縦軸
    if mmss:
        ax.set_ylabel("タイム (分:秒)", **_jp("タイム (分:秒)"))
        ax.yaxis.set_major_formatter(FuncFormatter(_mmss_formatter))
        # 最新値注釈（mm:ss）
        if y:
            _annotate_last(ax, x, y, _sec_to_mmss(y[-1]))
    else:
        ax.set_ylabel("タイム (秒)", **_jp("タイム (秒)"))
        if y:
            try:
                _annotate_last(ax, x, y, f"{float(y[-1]):.2f}s")
            except Exception:
                pass

    ax.grid(True, axis="y", alpha=0.3)

    if _JP_FONT_PROP is not None:
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            label.set_fontproperties(_JP_FONT_PROP)

    return fig


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    x = df["date"].tolist()
    y_rank = df["rank"].tolist() if "rank" in df.columns else []
    y_dev = df["deviation"].tolist() if "deviation" in df.columns else []

    ax1.plot(x, y_rank, label="順位", linewidth=2)
    ax2.plot(x, y_dev, label="偏差値")

    _setup_ax(ax1, "学業：順位・偏差値", "順位", "偏差値", period=period)

    if y_rank:
        try:
            _annotate_last(ax1, x, y_rank, f"{float(y_rank[-1]):.0f}")
        except Exception:
            pass
    if y_dev:
        try:
            _annotate_last(ax2, x, y_dev, f"{float(y_dev[-1]):.1f}")
        except Exception:
            pass

    if _JP_FONT_PROP is not None:
        ax1.legend(loc="upper left", prop=_JP_FONT_PROP)
        ax2.legend(loc="upper right", prop=_JP_FONT_PROP)
    else:
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right")

    return fig


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    x = df["date"].tolist()

    y_rating = df["rating"].tolist() if "rating" in df.columns else []
    ax1.plot(x, y_rating, label="評点", linewidth=2)

    subject_map = {
        "score_jp": "国語",
        "score_math": "数学",
        "score_en": "英語",
        "score_sci": "理科",
        "score_soc": "社会",
    }

    for col, jp in subject_map.items():
        if col in df.columns:
            y = df[col].tolist()
            ax2.plot(x, y, label=jp)

    _setup_ax(ax1, "学業：評点・教科スコア", "評点", "得点", period=period)

    # 最新値注釈（評点だけ）
    if y_rating:
        try:
            _annotate_last(ax1, x, y_rating, f"{float(y_rating[-1]):.1f}")
        except Exception:
            pass

    if _JP_FONT_PROP is not None:
        ax1.legend(loc="upper left", prop=_JP_FONT_PROP)
        ax2.legend(loc="upper right", prop=_JP_FONT_PROP, fontsize=8)
    else:
        ax1.legend(loc="upper left")
        ax2.legend(loc="upper right", fontsize=8)

    return fig
