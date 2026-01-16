from __future__ import annotations

from typing import Optional

# matplotlib は Streamlit Cloud で未導入のことがあるので optional import にする
try:
    import matplotlib.pyplot as plt  # type: ignore
    HAS_MPL = True
except Exception:
    plt = None  # type: ignore
    HAS_MPL = False


def _require_mpl():
    if not HAS_MPL or plt is None:
        raise ModuleNotFoundError(
            "matplotlib is required for report charts, but it is not installed. "
            "Please add 'matplotlib' to requirements.txt."
        )


def _empty_figure(title: str, message: str):
    """
    matplotlib が使える前提で、データ無し時の空図を返す
    """
    _require_mpl()
    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.axis("off")
    ax.text(0.5, 0.5, message, ha="center", va="center")
    return fig


def build_body_chart(df):
    """
    身長/体重/BMI（左: 身長, 右: 体重 & BMI）
    想定列: date, height_cm, weight_kg, bmi
    """
    _require_mpl()
    if df is None or getattr(df, "empty", True):
        return _empty_figure("身長 / 体重 / BMI", "期間内のデータがありません")

    fig, ax1 = plt.subplots()
    ax1.set_title("身長 / 体重 / BMI")
    ax1.set_xlabel("date")
    ax1.set_ylabel("height (cm)")

    x = df["date"]
    ax1.plot(x, df.get("height_cm"), label="height_cm")

    ax2 = ax1.twinx()
    ax2.set_ylabel("weight (kg) / bmi")
    if "weight_kg" in df.columns:
        ax2.plot(x, df["weight_kg"], label="weight_kg")
    if "bmi" in df.columns:
        ax2.plot(x, df["bmi"], label="bmi")

    # 凡例（左右まとめ）
    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.autofmt_xdate()
    return fig


def build_run_chart(df, col: str, title: str, y_label: str):
    """
    汎用の走力グラフ（秒は内部sec）
    """
    _require_mpl()
    if df is None or getattr(df, "empty", True) or col not in df.columns:
        return _empty_figure(title, "期間内のデータがありません")

    fig, ax = plt.subplots()
    ax.set_title(title)
    ax.set_xlabel("date")
    ax.set_ylabel(y_label)
    ax.plot(df["date"], df[col], label=col)
    ax.legend(loc="upper left")
    fig.autofmt_xdate()
    return fig


def build_school_overview_chart(df):
    """
    学業：順位＆偏差値（おすすめ分割の上段）
    左: 偏差値, 右: 順位（反転表示）
    想定列: date, deviation, rank
    """
    _require_mpl()
    if df is None or getattr(df, "empty", True):
        return _empty_figure("学業（順位 / 偏差値）", "期間内のデータがありません")

    fig, ax1 = plt.subplots()
    ax1.set_title("学業（順位 / 偏差値）")
    ax1.set_xlabel("date")

    x = df["date"]

    # deviation（左）
    if "deviation" in df.columns:
        ax1.set_ylabel("deviation")
        ax1.plot(x, df["deviation"], label="deviation")

    # rank（右・反転）
    ax2 = ax1.twinx()
    if "rank" in df.columns:
        ax2.set_ylabel("rank (smaller is better)")
        ax2.plot(x, df["rank"], label="rank")
        # 反転（上が良く見えるように）
        try:
            ax2.invert_yaxis()
        except Exception:
            pass

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.autofmt_xdate()
    return fig


def build_school_scores_chart(df):
    """
    学業：評点＆5教科（おすすめ分割の下段）
    左: rating, 右: score_*（複数）
    想定列: date, rating, score_jp, score_math, score_en, score_sci, score_soc
    """
    _require_mpl()
    if df is None or getattr(df, "empty", True):
        return _empty_figure("学業（評点 / 教科スコア）", "期間内のデータがありません")

    fig, ax1 = plt.subplots()
    ax1.set_title("学業（評点 / 教科スコア）")
    ax1.set_xlabel("date")

    x = df["date"]

    # rating（左）
    if "rating" in df.columns:
        ax1.set_ylabel("rating")
        ax1.plot(x, df["rating"], label="rating")

    # scores（右）
    ax2 = ax1.twinx()
    ax2.set_ylabel("scores")

    score_cols = [c for c in ["score_jp", "score_math", "score_en", "score_sci", "score_soc"] if c in df.columns]
    for c in score_cols:
        ax2.plot(x, df[c], label=c)

    h1, l1 = ax1.get_legend_handles_labels()
    h2, l2 = ax2.get_legend_handles_labels()
    ax1.legend(h1 + h2, l1 + l2, loc="upper left")

    fig.autofmt_xdate()
    return fig
