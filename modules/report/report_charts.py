# modules/report/report_charts.py
from __future__ import annotations

import os

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


def _require_mpl():
    if not HAS_MPL:
        raise ModuleNotFoundError(
            "matplotlib is required for report charts, but it is not installed."
        )


# =========================================================
# 日本語フォント対策（□ □ □ を直す本丸）
# =========================================================
def _setup_japanese_font():
    """
    Streamlit Cloud などは日本語フォントが入っていないことが多く、
    その場合 matplotlib は日本語を □□ で描画してしまう。

    対策：
      1) リポジトリにフォントを同梱（assets/fonts/）
      2) addfont して font.family を指定

    同梱フォント候補（どれか1つでOK）:
      - assets/fonts/NotoSansJP-Regular.otf
      - assets/fonts/IPAexGothic.ttf
    """
    _require_mpl()

    # 1) 同梱フォントがあれば最優先で使う
    here = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(here, "..", ".."))  # modules/report -> project root
    candidates = [
        os.path.join(project_root, "assets", "fonts", "NotoSansJP-Regular.otf"),
        os.path.join(project_root, "assets", "fonts", "NotoSansJP-Regular.ttf"),
        os.path.join(project_root, "assets", "fonts", "IPAexGothic.ttf"),
        os.path.join(project_root, "assets", "fonts", "ipag.ttf"),
        os.path.join(project_root, "assets", "fonts", "ipam.ttf"),
    ]

    for fp in candidates:
        if os.path.exists(fp):
            try:
                fm.fontManager.addfont(fp)
                prop = fm.FontProperties(fname=fp)
                name = prop.get_name()
                plt.rcParams["font.family"] = name
                plt.rcParams["axes.unicode_minus"] = False
                return True
            except Exception:
                pass

    # 2) 環境側に入っている日本語フォントを探す（入っていればOK）
    preferred_names = [
        "Noto Sans CJK JP",
        "Noto Sans JP",
        "IPAexGothic",
        "IPAGothic",
        "Yu Gothic",
        "MS Gothic",
        "TakaoGothic",
        "Hiragino Sans",
    ]
    try:
        installed = {f.name for f in fm.fontManager.ttflist}
        for name in preferred_names:
            if name in installed:
                plt.rcParams["font.family"] = name
                plt.rcParams["axes.unicode_minus"] = False
                return True
    except Exception:
        pass

    # 3) 見つからない場合：現状のまま（□□になる）
    #    ただし、ここまで来たら「フォント同梱が必要」が確定
    return False


# =========================================================
# 共通ユーティリティ
# =========================================================
def _format_date_range(df):
    """
    df["date"] は文字列 or datetime が来る想定
    """
    if df is None or df.empty or "date" not in df.columns:
        return ""
    try:
        import pandas as pd
        dt = pd.to_datetime(df["date"], errors="coerce")
        dt = dt.dropna()
        if dt.empty:
            return ""
        start = dt.min().date().isoformat()
        end = dt.max().date().isoformat()
        return f"{start} ～ {end}"
    except Exception:
        # 文字列フォールバック
        try:
            vals = [str(x) for x in df["date"].tolist() if str(x).strip()]
            if not vals:
                return ""
            return f"{vals[0]} ～ {vals[-1]}"
        except Exception:
            return ""


def _annotate_latest(ax, x_vals, y_vals, text, dy=0):
    """
    最後の点に注釈
    """
    if x_vals is None or y_vals is None:
        return
    if len(x_vals) == 0 or len(y_vals) == 0:
        return
    try:
        x = x_vals[-1]
        y = y_vals[-1]
        if y is None:
            return
        ax.annotate(
            text,
            xy=(x, y),
            xytext=(8, dy),
            textcoords="offset points",
            fontsize=10,
            va="center",
        )
    except Exception:
        return


def _sec_to_mmss(sec):
    """
    秒 -> m:ss（無効値は ""）
    """
    try:
        if sec is None:
            return ""
        s = float(sec)
        if s <= 0:
            return ""
        m = int(s) // 60
        r = int(round(s)) % 60
        return f"{m}:{r:02d}"
    except Exception:
        return ""


def _mmss_axis_formatter():
    """
    matplotlib のY軸を mm:ss 表示にする formatter
    """
    def _fmt(y, _pos=None):
        try:
            s = float(y)
            if s <= 0:
                return ""
            m = int(s) // 60
            r = int(round(s)) % 60
            return f"{m}:{r:02d}"
        except Exception:
            return ""
    return FuncFormatter(_fmt)


def _setup_ax(ax, title: str, ylabel_left: str | None = None, ylabel_right: str | None = None):
    ax.set_title(title)
    ax.grid(True, axis="y", alpha=0.3)
    if ylabel_left:
        ax.set_ylabel(ylabel_left)
    if ylabel_right:
        ax.right_ax.set_ylabel(ylabel_right)


# =========================================================
# P2: フィジカル（身長・体重・BMI）
# =========================================================
def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    _require_mpl()
    _setup_japanese_font()

    df = report.portfolio
    dr = _format_date_range(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2  # util 用

    x = df["date"].tolist()
    y_h = df["height_cm"].tolist()
    y_w = df["weight_kg"].tolist()

    ax1.plot(df["date"], df["height_cm"], label="身長（cm）", color="tab:blue")
    ax2.plot(df["date"], df["weight_kg"], label="体重（kg）", color="tab:orange")
    if "bmi" in df.columns:
        ax2.plot(df["date"], df["bmi"], label="BMI", color="tab:green", linestyle="--")

    title = "フィジカル成長（身長・体重・BMI）"
    if dr:
        title = f"{title}\n{dr}"

    _setup_ax(ax1, title, "身長（cm）", "体重（kg） / BMI")

    # 最新値注釈
    if len(y_h) > 0:
        _annotate_latest(ax1, x, y_h, f"{y_h[-1]:.1f}cm", dy=0)
    if len(y_w) > 0:
        _annotate_latest(ax2, x, y_w, f"{y_w[-1]:.1f}kg", dy=0)

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
    _setup_japanese_font()

    df = report.portfolio
    dr = _format_date_range(df)

    fig, ax = plt.subplots(figsize=(8, 4))

    x = df["date"].tolist()
    y = df[metric].tolist()

    ax.plot(df["date"], df[metric], marker="o")

    # タイトル（期間表示つき）
    t = title
    if dr:
        t = f"{t}\n{dr}"
    ax.set_title(t)

    # ラベル＆軸
    if mmss:
        ax.set_ylabel("タイム（分:秒）")
        ax.yaxis.set_major_formatter(_mmss_axis_formatter())
        latest_txt = _sec_to_mmss(y[-1]) if len(y) > 0 else ""
        if latest_txt:
            _annotate_latest(ax, x, y, latest_txt)
    else:
        ax.set_ylabel("タイム（秒）")
        if len(y) > 0 and y[-1] is not None:
            _annotate_latest(ax, x, y, f"{float(y[-1]):.2f}s")

    ax.grid(True, axis="y", alpha=0.3)

    return fig


# =========================================================
# P3: 学業（順位・偏差値）
# =========================================================
def fig_academic_position(report, show_roadmap: bool = True):
    _require_mpl()
    _setup_japanese_font()

    df = report.portfolio
    dr = _format_date_range(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    x = df["date"].tolist()
    y_rank = df["rank"].tolist()
    y_dev = df["deviation"].tolist()

    ax1.plot(df["date"], df["rank"], label="順位", color="tab:red")
    ax2.plot(df["date"], df["deviation"], label="偏差値", color="tab:blue")

    title = "学業（順位・偏差値）"
    if dr:
        title = f"{title}\n{dr}"

    _setup_ax(ax1, title, "順位", "偏差値")

    # 最新値注釈
    if len(y_rank) > 0 and y_rank[-1] is not None:
        _annotate_latest(ax1, x, y_rank, f"{float(y_rank[-1]):.0f}", dy=0)
    if len(y_dev) > 0 and y_dev[-1] is not None:
        _annotate_latest(ax2, x, y_dev, f"{float(y_dev[-1]):.1f}", dy=0)

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")

    return fig


# =========================================================
# P3: 学業（評点・各教科スコア）
# =========================================================
def fig_academic_scores_rating(report, show_roadmap: bool = True):
    _require_mpl()
    _setup_japanese_font()

    df = report.portfolio
    dr = _format_date_range(df)

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2

    x = df["date"].tolist()
    y_rating = df["rating"].tolist()

    ax1.plot(df["date"], df["rating"], label="評点", color="black", linewidth=2)

    subject_map = {
        "score_jp": "国語",
        "score_math": "数学",
        "score_en": "英語",
        "score_sci": "理科",
        "score_soc": "社会",
    }

    for col in ["score_jp", "score_math", "score_en", "score_sci", "score_soc"]:
        if col in df.columns:
            ax2.plot(df["date"], df[col], label=subject_map.get(col, col))

    title = "学業（評点・各教科スコア）"
    if dr:
        title = f"{title}\n{dr}"

    _setup_ax(ax1, title, "評点", "各教科スコア")

    # 最新値注釈（評点だけ）
    if len(y_rating) > 0 and y_rating[-1] is not None:
        _annotate_latest(ax1, x, y_rating, f"{float(y_rating[-1]):.1f}", dy=0)

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right", fontsize=8)

    return fig
