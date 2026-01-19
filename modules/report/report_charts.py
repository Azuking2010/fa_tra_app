# modules/report/report_charts.py
from __future__ import annotations

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    from matplotlib import font_manager as fm
    import os
    HAS_MPL = True
except Exception:
    plt = None
    FuncFormatter = None
    fm = None
    os = None
    HAS_MPL = False


def _require_mpl():
    if not HAS_MPL:
        raise ModuleNotFoundError(
            "matplotlib is required for report charts, but it is not installed."
        )


# =========================================================
# 日本語フォント（Noto Sans JP）設定
#  - Streamlit Cloud では OS に日本語フォントが無いことが多いので
#    assets/fonts 以下に ttf を置いてそれを読む
# =========================================================
_JP_FONT_PATHS = [
    # あなたの構成（スクショ）に合わせた候補
    "assets/fonts/Noto_Sans_JP/NotoSansJP-VariableFont_wght.ttf",
    "assets/fonts/NotoSansJP-VariableFont_wght.ttf",
    "assets/fonts/NotoSansJP-Regular.ttf",
]


def _apply_japanese_font():
    """日本語が □□ になる対策：ローカルTTFを読み込んで Matplotlib に設定する。"""
    _require_mpl()
    if fm is None or os is None:
        return

    # 既に設定済みなら二重登録しない
    if getattr(_apply_japanese_font, "_done", False):
        return

    font_path = None
    for p in _JP_FONT_PATHS:
        if os.path.exists(p):
            font_path = p
            break

    if font_path:
        try:
            fm.fontManager.addfont(font_path)
            fp = fm.FontProperties(fname=font_path)
            plt.rcParams["font.family"] = fp.get_name()
            plt.rcParams["axes.unicode_minus"] = False
        except Exception:
            # フォント登録に失敗しても落とさない（英語表示にフォールバック）
            pass

    _apply_japanese_font._done = True


# =========================================================
# 共通ユーティリティ
# =========================================================
def _setup_ax(ax, title: str, ylabel_left: str | None = None, ylabel_right: str | None = None):
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    if ylabel_left:
        ax.set_ylabel(ylabel_left)
    if ylabel_right:
        ax.right_ax.set_ylabel(ylabel_right)


def _period_str(df):
    """df['date'] の min〜max を 'YYYY-MM-DD 〜 YYYY-MM-DD' にする"""
    if df is None or df.empty or "date" not in df.columns:
        return ""
    try:
        dmin = str(df["date"].min())
        dmax = str(df["date"].max())
        if dmin and dmax:
            return f"{dmin} 〜 {dmax}"
    except Exception:
        return ""
    return ""


def _annotate_latest(ax, x, y, text: str):
    """最新点（最後の点）に注釈を付ける"""
    if x is None or y is None:
        return
    try:
        ax.annotate(
            text,
            xy=(x, y),
            xytext=(6, 0),
            textcoords="offset points",
            va="center",
            fontsize=9,
        )
    except Exception:
        pass


def _sec_to_mmss_str(sec):
    """秒 -> m:ss（不正値は空）"""
    try:
        if sec is None:
            return ""
        v = float(sec)
        if v <= 0:
            return ""
        s = int(round(v))
        m = s // 60
        ss = s % 60
        return f"{m}:{ss:02d}"
    except Exception:
        return ""


def _mmss_axis_formatter():
    """y軸の数値(=秒)を mm:ss 表示にする Formatter"""
    def _fmt(v, pos=None):
        try:
            if v is None:
                return ""
            vv = float(v)
            if vv <= 0:
                return ""
            s = int(round(vv))
            m = s // 60
            ss = s % 60
            return f"{m}:{ss:02d}"
        except Exception:
            return ""
    return FuncFormatter(_fmt)


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    _require_mpl()
    _apply_japanese_font()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2  # util 用

    ax1.plot(df["date"], df["height_cm"], label="身長 (cm)")
    ax2.plot(df["date"], df["weight_kg"], label="体重 (kg)")
    if "bmi" in df.columns:
        ax2.plot(df["date"], df["bmi"], label="BMI", linestyle="--")

    title = "フィジカル推移（身長・体重・BMI）"
    if period:
        title = f"{title}\n{period}"

    _setup_ax(ax1, title, "身長 (cm)", "体重 (kg) / BMI")

    # 最新値注釈
    try:
        if not df.empty:
            x_last = df["date"].iloc[-1]
            h_last = df["height_cm"].iloc[-1] if "height_cm" in df.columns else None
            w_last = df["weight_kg"].iloc[-1] if "weight_kg" in df.columns else None
            b_last = df["bmi"].iloc[-1] if "bmi" in df.columns else None

            if h_last is not None:
                _annotate_latest(ax1, x_last, h_last, f"{float(h_last):.1f}cm")
            if w_last is not None:
                _annotate_latest(ax2, x_last, w_last, f"{float(w_last):.1f}kg")
            if b_last is not None:
                try:
                    _annotate_latest(ax2, x_last, b_last, f"{float(b_last):.2f}")
                except Exception:
                    pass
    except Exception:
        pass

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
    """
    metric: df列名（例 run_100m_sec / run_1500m_sec / run_3000m_sec）
    mmss: True のとき、y軸表示を mm:ss（※値は秒のまま）
    """
    _require_mpl()
    _apply_japanese_font()

    df = report.portfolio
    period = _period_str(df)

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(df["date"], df[metric], marker="o")

    # タイトル（期間付き）
    if period:
        ax.set_title(f"{title}\n{period}")
    else:
        ax.set_title(title)

    # y軸ラベル＆フォーマット
    if mmss:
        ax.set_ylabel("タイム（分:秒）")
        ax.yaxis.set_major_formatter(_mmss_axis_formatter())
    else:
        ax.set_ylabel("タイム（秒）")

    ax.grid(True, axis="y", alpha=0.3)

    # 最新値注釈（最後の点）
    try:
        if not df.empty:
            x_last = df["date"].iloc[-1]
            y_last = df[metric].iloc[-1]
            if mmss:
                t = _sec_to_mmss_str(y_last)
                if t:
                    _annotate_latest(ax, x_last, y_last, t)
            else:
                _annotate_latest(ax, x_last, y_last, f"{float(y_last):.2f}s")
    except Exception:
        pass

    return fig


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    _require_mpl()
    _apply_japanese_font()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rank"], label="学年順位", linestyle="-", marker="o")
    ax2.plot(df["date"], df["deviation"], label="偏差値", linestyle="-", marker="o")

    title = "学業推移（順位・偏差値）"
    if period:
        title = f"{title}\n{period}"

    _setup_ax(ax1, title, "学年順位（小さいほど上位）", "偏差値")

    # 最新値注釈
    try:
        if not df.empty:
            x_last = df["date"].iloc[-1]
            r_last = df["rank"].iloc[-1] if "rank" in df.columns else None
            d_last = df["deviation"].iloc[-1] if "deviation" in df.columns else None
            if r_last is not None:
                _annotate_latest(ax1, x_last, r_last, f"{int(round(float(r_last)))}位")
            if d_last is not None:
                _annotate_latest(ax2, x_last, d_last, f"{float(d_last):.1f}")
    except Exception:
        pass

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    return fig


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    _require_mpl()
    _apply_japanese_font()

    df = report.portfolio
    period = _period_str(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    ax1.plot(df["date"], df["rating"], label="評点", linewidth=2, marker="o")

    subject_map = {
        "score_jp": "国語",
        "score_math": "数学",
        "score_en": "英語",
        "score_sci": "理科",
        "score_soc": "社会",
    }

    for col, jp in subject_map.items():
        if col in df.columns:
            ax2.plot(df["date"], df[col], label=jp, marker="o")

    title = "学業推移（評点・教科スコア）"
    if period:
        title = f"{title}\n{period}"

    _setup_ax(ax1, title, "評点", "教科スコア")

    # 最新値注釈（評点のみ）
    try:
        if not df.empty:
            x_last = df["date"].iloc[-1]
            y_last = df["rating"].iloc[-1] if "rating" in df.columns else None
            if y_last is not None:
                _annotate_latest(ax1, x_last, y_last, f"{float(y_last):.1f}")
    except Exception:
        pass

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)

    return fig
