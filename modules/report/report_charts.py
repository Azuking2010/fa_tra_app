# modules/report/report_charts.py
from __future__ import annotations

# matplotlib は Cloud 環境で未導入のことがあるため optional import
try:
    import matplotlib.pyplot as plt
    from matplotlib.ticker import FuncFormatter
    HAS_MPL = True
except Exception:
    plt = None
    FuncFormatter = None
    HAS_MPL = False


def _enable_japanese_font():
    """
    Streamlit Cloud で日本語が「□」になる問題対策。
    最優先：japanize-matplotlib（requirements に追加推奨）
    """
    if not HAS_MPL:
        return

    # 1) まず japanize_matplotlib を試す（これが一番安定）
    try:
        import japanize_matplotlib  # noqa: F401
        return
    except Exception:
        pass

    # 2) フォールバック：環境にある日本語フォントを探して設定
    # （Cloud環境によっては入ってない場合あり。その場合は □ のまま）
    try:
        from matplotlib import font_manager, rcParams

        candidates = [
            "Noto Sans CJK JP",
            "Noto Sans JP",
            "IPAexGothic",
            "IPAPGothic",
            "TakaoGothic",
            "Yu Gothic",
            "Hiragino Sans",
            "MS Gothic",
        ]

        available = {f.name for f in font_manager.fontManager.ttflist}
        for name in candidates:
            if name in available:
                rcParams["font.family"] = name
                return
    except Exception:
        pass


def _require_mpl():
    if not HAS_MPL:
        raise ModuleNotFoundError(
            "matplotlib is required for report charts, but it is not installed."
        )
    _enable_japanese_font()
    # マイナス記号が文字化けする環境対策
    try:
        import matplotlib as mpl
        mpl.rcParams["axes.unicode_minus"] = False
    except Exception:
        pass


# =========================================================
# 共通ユーティリティ
# =========================================================
def _date_range_label(report) -> str:
    """タイトルに入れる期間表示（YYYY-MM-DD 〜 YYYY-MM-DD）"""
    try:
        df = report.portfolio
        if df is None or df.empty:
            return ""
        start = str(df["date"].iloc[0])
        end = str(df["date"].iloc[-1])
        return f"{start} 〜 {end}"
    except Exception:
        return ""


def _setup_ax(ax, title: str, ylabel_left: str | None = None, ylabel_right: str | None = None):
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    if ylabel_left:
        ax.set_ylabel(ylabel_left)
    if ylabel_right:
        ax.right_ax.set_ylabel(ylabel_right)


def _annotate_latest(ax, x_values, y_values, text: str, dx: int = 8, dy: int = 0):
    """最新点に数値注釈（右側に表示）"""
    try:
        if x_values is None or y_values is None:
            return
        if len(x_values) == 0 or len(y_values) == 0:
            return
        x = x_values[-1]
        y = y_values[-1]
        if y is None:
            return
        ax.annotate(
            text,
            xy=(x, y),
            xytext=(dx, dy),
            textcoords="offset points",
            va="center",
            fontsize=10,
        )
    except Exception:
        return


def _sec_to_mmss(sec: float) -> str:
    try:
        s = float(sec)
        if s <= 0:
            return "—"
        m = int(s) // 60
        ss = int(round(s)) % 60
        return f"{m}:{ss:02d}"
    except Exception:
        return "—"


def _fmt_mmss_tick(x, _pos=None):
    return _sec_to_mmss(x)


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _date_range_label(report)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2  # util 用

    # データ
    x = df["date"].tolist()
    h = df["height_cm"].tolist() if "height_cm" in df.columns else []
    w = df["weight_kg"].tolist() if "weight_kg" in df.columns else []
    b = df["bmi"].tolist() if "bmi" in df.columns else None

    # 描画
    if h:
        ax1.plot(x, h, label="身長 (cm)")
        _annotate_latest(ax1, x, h, f"{h[-1]:.1f}cm", dx=8, dy=10)

    if w:
        ax2.plot(x, w, label="体重 (kg)")
        _annotate_latest(ax2, x, w, f"{w[-1]:.1f}kg", dx=8, dy=-10)

    if b is not None:
        ax2.plot(x, b, label="BMI", linestyle="--")
        try:
            _annotate_latest(ax2, x, b, f"{float(b[-1]):.1f}", dx=8, dy=12)
        except Exception:
            pass

    title = "フィジカル推移"
    if period:
        title = f"{title}\n{period}"

    _setup_ax(ax1, title, "身長 (cm)", "体重 / BMI")

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
    period = _date_range_label(report)

    fig, ax = plt.subplots(figsize=(8, 4))

    x = df["date"].tolist()
    y = df[metric].tolist() if metric in df.columns else []

    ax.plot(x, y, marker="o")

    # タイトル（期間つき）
    full_title = title
    if period:
        full_title = f"{title}\n{period}"
    ax.set_title(full_title)

    # 軸ラベル＆mm:ss
    if mmss:
        ax.set_ylabel("タイム (分:秒)")
        ax.yaxis.set_major_formatter(FuncFormatter(_fmt_mmss_tick))
        # 最新値注釈も mm:ss
        if y:
            _annotate_latest(ax, x, y, _sec_to_mmss(y[-1]))
    else:
        ax.set_ylabel("タイム (秒)")
        if y:
            try:
                _annotate_latest(ax, x, y, f"{float(y[-1]):.2f}s")
            except Exception:
                pass

    ax.grid(True, axis="y", alpha=0.3)

    return fig


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _date_range_label(report)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    x = df["date"].tolist()
    r = df["rank"].tolist() if "rank" in df.columns else []
    d = df["deviation"].tolist() if "deviation" in df.columns else []

    if r:
        ax1.plot(x, r, label="学年順位", linewidth=2)
        try:
            _annotate_latest(ax1, x, r, f"{float(r[-1]):.0f}位", dx=8, dy=10)
        except Exception:
            pass

    if d:
        ax2.plot(x, d, label="偏差値")
        try:
            _annotate_latest(ax2, x, d, f"{float(d[-1]):.1f}", dx=8, dy=-10)
        except Exception:
            pass

    title = "学業：順位・偏差値"
    if period:
        title = f"{title}\n{period}"

    _setup_ax(ax1, title, "順位 (位)", "偏差値")
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    return fig


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    _require_mpl()

    df = report.portfolio
    period = _date_range_label(report)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    x = df["date"].tolist()

    # 評点（左）
    if "rating" in df.columns:
        rating = df["rating"].tolist()
        ax1.plot(x, rating, label="評点", linewidth=2)
        try:
            _annotate_latest(ax1, x, rating, f"{float(rating[-1]):.1f}", dx=8, dy=10)
        except Exception:
            pass

    # 各教科（右）
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

    title = "学業：評点・教科スコア"
    if period:
        title = f"{title}\n{period}"

    _setup_ax(ax1, title, "評点", "得点")
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)

    return fig
