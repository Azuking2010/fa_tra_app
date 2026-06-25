# file: modules/ui_analyst_report.py
# purpose: portfolioシートを読み取り専用で使い、身体・タイム・学業・count系を可視化する分析ページ。
#          既存機能を壊さないため、Sheetsには書き込まず、App側でグラフ化だけ行う。

from __future__ import annotations

import re
from html import escape
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as _st

import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import FuncFormatter


ANALYST_CACHE_TTL_SECONDS = 60 * 60 * 12  # 12時間

FONT_DIR = Path("assets/fonts/Noto_Sans_JP")

BASE_PORTFOLIO_COLUMNS = [
    "date",
    "height_cm",
    "weight_kg",
    "run_50m_sec",
    "run_100m_sec",  # 旧列名。互換用。中身は50mとして扱う。
    "run_1500m_sec",
    "run_3000m_sec",
    "track_meet",
    "rank",
    "deviation",
    "rating",
    "score_jp",
    "score_math",
    "score_en",
    "score_sci",
    "score_soc",
    "tcenter",
    "soccer_tournament",
    "match_result",
    "video_url",
    "video_note",
    "note",
    "period_start",
    "period_end",
    "record_type",
    "source_id",
    "analyst_note",
]

COUNT_LABELS = {
    "stretch_count": "ストレッチ",
    "scanning_count": "首振り",
    "effective_receive_count": "効果的な受け方",
    "chance_creation_count": "チャンス創出",
    "assist_count": "アシスト",
    "goal_count": "ゴール",
    "shot_count": "シュート",
    "left_foot_shot_count": "左足シュート",
    "u14_match_count": "U14試合",
    "u15_squad_count": "U15帯同",
    "practice_log_count": "練習後メモ",
    "study_log_count": "勉強記録",
}

SCORE_COLS = [
    ("score_jp", "国語"),
    ("score_math", "数学"),
    ("score_en", "英語"),
    ("score_sci", "理科"),
    ("score_soc", "社会"),
]

EVENT_COLUMNS = [
    "date",
    "track_meet",
    "soccer_tournament",
    "match_result",
    "video_note",
    "note",
    "analyst_note",
    "video_url",
]

COLOR_HEIGHT = "#0AA7C8"
COLOR_WEIGHT = "#F0A202"
COLOR_50 = "#DC2626"
COLOR_1500 = "#2563EB"
COLOR_3000 = "#7C3AED"
COLOR_RANK = "#16A34A"
COLOR_DEVIATION = "#0891B2"
COLOR_RATING = "#EA580C"
COLOR_GRID = "#DDEAF0"

MULTI_COLORS = [
    "#2563EB",
    "#DC2626",
    "#16A34A",
    "#9333EA",
    "#EA580C",
    "#0891B2",
    "#BE123C",
    "#4F46E5",
]


@_st.cache_data(ttl=ANALYST_CACHE_TTL_SECONDS, show_spinner=False)
def _load_portfolio_cached(_storage, storage_key: str, cache_version: int) -> pd.DataFrame:
    """
    portfolioを12時間キャッシュして読み込む。

    重要：
    storage.load_all_portfolio() は既定列だけに絞り込む実装の場合がある。
    今後portfolioに列を追加して分析したいため、SheetsStorageの場合は
    worksheetを読み取り専用で直接読む。
    """
    try:
        if hasattr(_storage, "_open_ws") and hasattr(_storage, "portfolio_worksheet_name"):
            ws = _storage._open_ws(_storage.portfolio_worksheet_name)
            values = ws.get_all_values()

            if not values:
                return pd.DataFrame(columns=BASE_PORTFOLIO_COLUMNS)

            header = values[0]
            rows = values[1:]

            if not header:
                return pd.DataFrame(columns=BASE_PORTFOLIO_COLUMNS)

            return pd.DataFrame(rows, columns=header)

    except Exception:
        pass

    return _storage.load_all_portfolio()


@_st.cache_resource(show_spinner=False)
def _configure_matplotlib_font() -> str:
    """
    assets/fonts/Noto_Sans_JP 配下の日本語フォントをmatplotlibに登録する。
    見つからない場合は、環境デフォルトのフォントで描画する。
    """
    try:
        if not FONT_DIR.exists():
            plt.rcParams["axes.unicode_minus"] = False
            return ""

        font_files = []
        for pattern in ["**/*Regular*.ttf", "**/*Regular*.otf", "**/*.ttf", "**/*.otf"]:
            font_files.extend(FONT_DIR.glob(pattern))

        font_files = sorted(set(font_files))
        if not font_files:
            plt.rcParams["axes.unicode_minus"] = False
            return ""

        font_path = font_files[0]
        font_manager.fontManager.addfont(str(font_path))
        font_name = font_manager.FontProperties(fname=str(font_path)).get_name()

        plt.rcParams["font.family"] = font_name
        plt.rcParams["axes.unicode_minus"] = False
        return font_name

    except Exception:
        plt.rcParams["axes.unicode_minus"] = False
        return ""


def _inject_analyst_css(st) -> None:
    st.markdown(
        """
<style>
.analyst-hero {
    background: linear-gradient(135deg, #f5fbff 0%, #ffffff 72%);
    border: 2px solid #0aa7c8;
    border-radius: 18px;
    padding: 22px 24px;
    margin: 16px 0 24px 0;
}

.analyst-hero-title {
    font-size: 30px;
    font-weight: 900;
    color: #063849;
    margin-bottom: 8px;
}

.analyst-hero-sub {
    font-size: 17px;
    color: #32606d;
    line-height: 1.7;
}

.analyst-section-title {
    font-size: 25px;
    font-weight: 900;
    color: #063849;
    margin: 28px 0 14px 0;
}

.analyst-filter-card {
    background: #ffffff;
    border: 1.5px solid #b9e6ef;
    border-radius: 16px;
    padding: 14px 16px;
    margin: 10px 0 22px 0;
}

.analyst-kpi-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin: 8px 0 22px 0;
}

.analyst-kpi-card {
    background: #ffffff;
    border: 1.5px solid #b9e6ef;
    border-radius: 16px;
    padding: 14px 15px;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.04);
}

.analyst-kpi-label {
    color: #0a6478;
    font-size: 15px;
    font-weight: 900;
    margin-bottom: 6px;
}

.analyst-kpi-value {
    color: #062f3d;
    font-size: 26px;
    font-weight: 950;
    line-height: 1.3;
}

.analyst-kpi-sub {
    color: #52717c;
    font-size: 14px;
    line-height: 1.6;
    margin-top: 4px;
}

.analyst-chart-title {
    color: #063849;
    font-size: 22px;
    font-weight: 900;
    margin: 18px 0 2px 0;
}

.analyst-chart-sub {
    color: #52717c;
    font-size: 14px;
    line-height: 1.6;
    margin-bottom: 10px;
}

.analyst-empty {
    color: #7b8b92;
    font-size: 16px;
    padding: 10px 0;
}

@media (max-width: 900px) {
    .analyst-hero {
        padding: 18px 16px;
    }

    .analyst-hero-title {
        font-size: 25px;
    }

    .analyst-hero-sub {
        font-size: 16px;
    }

    .analyst-kpi-grid {
        grid-template-columns: 1fr;
    }

    .analyst-chart-title {
        font-size: 20px;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )


def _is_blank(value: Any) -> bool:
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except Exception:
        pass

    s = str(value).strip()
    return s == "" or s.lower() in ["nan", "none", "null"]


def _txt(value: Any, fallback: str = "") -> str:
    if _is_blank(value):
        return fallback
    return str(value).strip()


def _norm_number_text(value: Any) -> str:
    if _is_blank(value):
        return ""

    text = str(value).strip()
    text = text.replace(",", "")
    text = text.replace("秒", "")
    text = text.replace("cm", "")
    text = text.replace("kg", "")
    text = text.replace("ＣＭ", "")
    text = text.replace("ＫＧ", "")
    text = text.replace("点", "")
    text = text.replace("位", "")
    return text.strip()


def _parse_float(value: Any) -> float | None:
    text = _norm_number_text(value)
    if not text:
        return None

    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None

    try:
        return float(match.group(0))
    except Exception:
        return None


def _parse_seconds(value: Any) -> float | None:
    """
    秒数列用。
    原則は 275 のような秒入力。
    誤って 4:35 のように入れても読めるようにする。
    """
    if _is_blank(value):
        return None

    text = str(value).strip()

    mmss = re.match(r"^\s*(\d{1,2})\s*[:：]\s*(\d{1,2})\s*$", text)
    if mmss:
        minutes = int(mmss.group(1))
        seconds = int(mmss.group(2))
        if 0 <= seconds < 60:
            return float(minutes * 60 + seconds)

    return _parse_float(value)


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df is None:
        df = pd.DataFrame()

    d = df.copy()

    for c in columns:
        if c not in d.columns:
            d[c] = ""

    return d


def _build_storage_key(storage) -> str:
    try:
        info = storage.get_info() or {}
    except Exception:
        info = {}

    parts = [
        str(info.get("spreadsheet_id", "")),
        str(info.get("portfolio_worksheet", "portfolio")),
    ]
    return "|".join(parts)


def _clean_portfolio(df: pd.DataFrame) -> pd.DataFrame:
    d = _ensure_columns(df, BASE_PORTFOLIO_COLUMNS)

    if d.empty:
        return d

    d = d.copy()
    d["_row_order"] = range(len(d))
    d["_date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["_date"]).copy()

    if d.empty:
        return d

    d["_date_only"] = d["_date"].dt.date
    d = d.sort_values(["_date", "_row_order"], ascending=[True, True]).reset_index(drop=True)
    return d


def _filter_by_period(st, df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df

    min_date = df["_date_only"].min()
    max_date = df["_date_only"].max()

    st.markdown('<div class="analyst-section-title">表示期間</div>', unsafe_allow_html=True)

    with st.container():
        st.markdown('<div class="analyst-filter-card">', unsafe_allow_html=True)

        c1, c2 = st.columns(2)

        start_date = c1.date_input(
            "開始日",
            value=min_date,
            min_value=min_date,
            max_value=max_date,
            key="analyst_start_date",
        )

        end_date = c2.date_input(
            "終了日",
            value=max_date,
            min_value=min_date,
            max_value=max_date,
            key="analyst_end_date",
        )

        st.markdown("</div>", unsafe_allow_html=True)

    if start_date > end_date:
        st.warning("開始日が終了日より後になっています。期間を確認してください。")
        return df.iloc[0:0].copy()

    filtered = df[(df["_date_only"] >= start_date) & (df["_date_only"] <= end_date)].copy()

    st.caption(f"表示対象：{start_date} 〜 {end_date} / {len(filtered)}行")

    return filtered.reset_index(drop=True)


def _first_non_empty_value(row: pd.Series, columns: list[str]) -> Any:
    for col in columns:
        if col in row.index and not _is_blank(row.get(col)):
            return row.get(col)
    return None


def _metric_points(df: pd.DataFrame, value_cols: list[str], value_type: str) -> pd.DataFrame:
    """
    metricごとの有効値だけを抽出する。
    同じ日付に複数行ある場合は、その日付の最後の非空値を採用する。
    """
    empty_cols = ["_date", "_date_only", "value", "date_label", "track_meet", "note"]

    if df is None or df.empty:
        return pd.DataFrame(columns=empty_cols)

    d = df.copy()

    raw_values = d.apply(lambda row: _first_non_empty_value(row, value_cols), axis=1)

    if value_type == "seconds":
        values = raw_values.apply(_parse_seconds)
    else:
        values = raw_values.apply(_parse_float)

    d["value"] = values
    d = d.dropna(subset=["value"]).copy()
    d = d[d["value"] > 0].copy()

    if d.empty:
        return pd.DataFrame(columns=empty_cols)

    d = d.sort_values(["_date", "_row_order"], ascending=[True, True])

    # 同一日付では最後の非空値を採用
    d = d.groupby("_date_only", as_index=False).last()

    d["_date"] = pd.to_datetime(d["_date_only"])
    d["date_label"] = d["_date"].dt.strftime("%Y-%m-%d")

    for c in empty_cols:
        if c not in d.columns:
            d[c] = ""

    return d[empty_cols].sort_values("_date").reset_index(drop=True)


def _metric_points_single(df: pd.DataFrame, value_col: str, value_type: str = "float") -> pd.DataFrame:
    return _metric_points(df, [value_col], value_type)


def _format_seconds(total_seconds: Any) -> str:
    try:
        sec = int(round(float(total_seconds)))
    except Exception:
        return "—"

    if sec <= 0:
        return "—"

    minutes = sec // 60
    seconds = sec % 60
    return f"{minutes}:{seconds:02d}"


def _format_metric_value(value: Any, metric_key: str) -> str:
    try:
        v = float(value)
    except Exception:
        return "—"

    if metric_key == "height":
        return f"{v:.1f} cm"

    if metric_key == "weight":
        return f"{v:.1f} kg"

    if metric_key in ["run_50", "run_1500", "run_3000"]:
        return _format_seconds(v)

    if metric_key == "rank":
        return f"{int(round(v))} 位"

    if metric_key == "deviation":
        return f"{v:.1f}"

    if metric_key == "rating":
        return f"{v:.1f}"

    return f"{v:g}"


def _format_delta(first_value: Any, latest_value: Any, metric_key: str, count: int) -> str:
    if count <= 1:
        return "記録1件"

    try:
        first = float(first_value)
        latest = float(latest_value)
    except Exception:
        return f"記録{count}件"

    if metric_key == "height":
        diff = latest - first
        if abs(diff) < 0.05:
            return f"初回比 ±0.0 cm / 記録{count}件"
        sign = "+" if diff > 0 else ""
        return f"初回比 {sign}{diff:.1f} cm / 記録{count}件"

    if metric_key == "weight":
        diff = latest - first
        if abs(diff) < 0.05:
            return f"初回比 ±0.0 kg / 記録{count}件"
        sign = "+" if diff > 0 else ""
        return f"初回比 {sign}{diff:.1f} kg / 記録{count}件"

    if metric_key in ["run_50", "run_1500", "run_3000"]:
        diff = first - latest
        if abs(diff) < 0.5:
            return f"初回比 変化なし / 記録{count}件"
        if diff > 0:
            return f"初回比 {int(round(diff))}秒短縮 / 記録{count}件"
        return f"初回比 {int(round(abs(diff)))}秒増加 / 記録{count}件"

    if metric_key == "rank":
        diff = first - latest
        if abs(diff) < 0.5:
            return f"初回比 変化なし / 記録{count}件"
        if diff > 0:
            return f"初回比 {int(round(diff))}位アップ / 記録{count}件"
        return f"初回比 {int(round(abs(diff)))}位ダウン / 記録{count}件"

    diff = latest - first
    if abs(diff) < 0.05:
        return f"初回比 変化なし / 記録{count}件"
    sign = "+" if diff > 0 else ""
    return f"初回比 {sign}{diff:.1f} / 記録{count}件"


def _latest_card_html(label: str, points: pd.DataFrame, metric_key: str) -> str:
    safe_label = escape(label)

    if points is None or points.empty:
        return f"""
<div class="analyst-kpi-card">
  <div class="analyst-kpi-label">{safe_label}</div>
  <div class="analyst-kpi-value">—</div>
  <div class="analyst-kpi-sub">この期間の記録はありません</div>
</div>
"""

    first = points.iloc[0]
    latest = points.iloc[-1]

    value_text = escape(_format_metric_value(latest.get("value"), metric_key))
    date_text = escape(_txt(latest.get("date_label"), "日付未設定"))
    delta_text = escape(_format_delta(first.get("value"), latest.get("value"), metric_key, len(points)))

    return f"""
<div class="analyst-kpi-card">
  <div class="analyst-kpi-label">{safe_label}</div>
  <div class="analyst-kpi-value">{value_text}</div>
  <div class="analyst-kpi-sub">{date_text}<br>{delta_text}</div>
</div>
"""


def _render_hero(st) -> None:
    st.markdown(
        """
<div class="analyst-hero">
  <div class="analyst-hero-title">📊 Analyst Report</div>
  <div class="analyst-hero-sub">
    身体・タイム・学業・行動countを分析するページです。Sheetsのportfolioを読み取り専用で表示します。
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_latest_cards(
    st,
    height_points: pd.DataFrame,
    weight_points: pd.DataFrame,
    run50_points: pd.DataFrame,
    run1500_points: pd.DataFrame,
    run3000_points: pd.DataFrame,
) -> None:
    st.markdown('<div class="analyst-section-title">最新サマリー</div>', unsafe_allow_html=True)

    cards = [
        _latest_card_html("身長", height_points, "height"),
        _latest_card_html("体重", weight_points, "weight"),
        _latest_card_html("50m", run50_points, "run_50"),
        _latest_card_html("1500m", run1500_points, "run_1500"),
        _latest_card_html("3000m", run3000_points, "run_3000"),
    ]

    st.markdown(
        f"""
<div class="analyst-kpi-grid">
  {''.join(cards)}
</div>
""",
        unsafe_allow_html=True,
    )


def _style_axis(ax) -> None:
    ax.grid(True, axis="y", color=COLOR_GRID, linewidth=1, alpha=0.9)
    ax.grid(True, axis="x", color=COLOR_GRID, linewidth=0.5, alpha=0.35)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.tick_params(axis="x", labelrotation=30)


def _render_chart_title(st, title: str, sub: str) -> None:
    st.markdown(
        f"""
<div class="analyst-chart-title">{escape(title)}</div>
<div class="analyst-chart-sub">{escape(sub)}</div>
""",
        unsafe_allow_html=True,
    )


def _show_pyplot(st, fig) -> None:
    try:
        st.pyplot(fig, use_container_width=True)
    except TypeError:
        st.pyplot(fig)
    finally:
        plt.close(fig)


def _plot_body_chart(st, height_points: pd.DataFrame, weight_points: pd.DataFrame) -> None:
    _render_chart_title(
        st,
        "身長・体重",
        "左軸：身長cm / 右軸：体重kg。身体の変化を確認します。",
    )

    has_height = height_points is not None and not height_points.empty
    has_weight = weight_points is not None and not weight_points.empty

    if not has_height and not has_weight:
        st.info("この期間に身長・体重の記録はありません。")
        return

    fig, ax1 = plt.subplots(figsize=(8.5, 4.6))
    fig.patch.set_facecolor("#ffffff")
    ax1.set_facecolor("#ffffff")

    lines = []
    labels = []

    if has_height:
        line_h, = ax1.plot(
            height_points["_date"],
            height_points["value"],
            marker="o",
            linewidth=2.8,
            color=COLOR_HEIGHT,
            label="身長 cm",
        )
        lines.append(line_h)
        labels.append("身長 cm")
        ax1.set_ylabel("身長 (cm)", color=COLOR_HEIGHT)
        ax1.tick_params(axis="y", labelcolor=COLOR_HEIGHT)

    if has_weight:
        if has_height:
            ax2 = ax1.twinx()
        else:
            ax2 = ax1

        ax2.set_facecolor("#ffffff")
        line_w, = ax2.plot(
            weight_points["_date"],
            weight_points["value"],
            marker="o",
            linewidth=2.8,
            color=COLOR_WEIGHT,
            label="体重 kg",
        )
        lines.append(line_w)
        labels.append("体重 kg")
        ax2.set_ylabel("体重 (kg)", color=COLOR_WEIGHT)
        ax2.tick_params(axis="y", labelcolor=COLOR_WEIGHT)

        if has_height:
            ax2.spines["top"].set_visible(False)

    ax1.set_xlabel("日付")
    _style_axis(ax1)
    ax1.legend(lines, labels, loc="best")

    fig.tight_layout()
    _show_pyplot(st, fig)


def _plot_time_chart(
    st,
    points: pd.DataFrame,
    title: str,
    sub: str,
    color: str,
) -> None:
    _render_chart_title(st, title, sub)

    if points is None or points.empty:
        st.info(f"この期間に{title}の記録はありません。")
        return

    fig, ax = plt.subplots(figsize=(8.5, 4.3))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    ax.plot(
        points["_date"],
        points["value"],
        marker="o",
        linewidth=2.8,
        color=color,
    )

    ax.set_xlabel("日付")
    ax.set_ylabel("タイム")
    ax.yaxis.set_major_formatter(FuncFormatter(lambda x, pos: _format_seconds(x)))

    # 重要：タイムは小さいほど速い。
    # グラフ上では「上がる＝速くなる」にしたいため、y軸を反転する。
    ax.invert_yaxis()

    _style_axis(ax)

    latest = points.iloc[-1]
    ax.annotate(
        _format_seconds(latest["value"]),
        xy=(latest["_date"], latest["value"]),
        xytext=(8, 8),
        textcoords="offset points",
        fontsize=11,
        weight="bold",
        color=color,
    )

    fig.tight_layout()
    _show_pyplot(st, fig)


def _plot_single_metric_chart(
    st,
    points: pd.DataFrame,
    title: str,
    sub: str,
    ylabel: str,
    color: str,
    metric_key: str,
    invert_y: bool = False,
) -> None:
    _render_chart_title(st, title, sub)

    if points is None or points.empty:
        st.info(f"この期間に{title}の記録はありません。")
        return

    fig, ax = plt.subplots(figsize=(8.5, 4.1))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    ax.plot(
        points["_date"],
        points["value"],
        marker="o",
        linewidth=2.6,
        color=color,
    )

    ax.set_xlabel("日付")
    ax.set_ylabel(ylabel)

    if invert_y:
        ax.invert_yaxis()

    _style_axis(ax)

    latest = points.iloc[-1]
    ax.annotate(
        _format_metric_value(latest["value"], metric_key),
        xy=(latest["_date"], latest["value"]),
        xytext=(8, 8),
        textcoords="offset points",
        fontsize=11,
        weight="bold",
        color=color,
    )

    fig.tight_layout()
    _show_pyplot(st, fig)


def _plot_multi_line_chart(
    st,
    df: pd.DataFrame,
    metric_defs: list[tuple[str, str]],
    title: str,
    sub: str,
    ylabel: str,
) -> None:
    _render_chart_title(st, title, sub)

    if df is None or df.empty:
        st.info(f"この期間に{title}の記録はありません。")
        return

    series_list = []

    for col, label in metric_defs:
        points = _metric_points_single(df, col, "float")
        if points is not None and not points.empty:
            series_list.append((label, points))

    if not series_list:
        st.info(f"この期間に{title}の記録はありません。")
        return

    fig, ax = plt.subplots(figsize=(8.5, 4.5))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    for idx, (label, points) in enumerate(series_list):
        color = MULTI_COLORS[idx % len(MULTI_COLORS)]
        ax.plot(
            points["_date"],
            points["value"],
            marker="o",
            linewidth=2.3,
            color=color,
            label=label,
        )

    ax.set_xlabel("日付")
    ax.set_ylabel(ylabel)
    _style_axis(ax)
    ax.legend(loc="best")

    fig.tight_layout()
    _show_pyplot(st, fig)


def _count_columns_in_df(df: pd.DataFrame) -> list[str]:
    if df is None or df.empty:
        return []

    cols = []

    for c in df.columns:
        if c in COUNT_LABELS:
            cols.append(c)
            continue

        if c.endswith("_count"):
            cols.append(c)

    unique_cols = []
    for c in cols:
        if c not in unique_cols:
            unique_cols.append(c)

    return unique_cols


def _count_label(col: str) -> str:
    if col in COUNT_LABELS:
        return COUNT_LABELS[col]

    label = col
    label = label.replace("_count", "")
    label = label.replace("_", " ")
    return label


def _plot_count_summary(st, df: pd.DataFrame) -> None:
    _render_chart_title(
        st,
        "行動countサマリー",
        "portfolioに追加した *_count 列を、選択期間の合計として表示します。",
    )

    count_cols = _count_columns_in_df(df)

    if not count_cols:
        st.info("count列はまだありません。stretch_count や scanning_count などをportfolio右側に追加すると表示できます。")
        return

    values = []

    for col in count_cols:
        total = 0.0
        for v in df[col].tolist():
            parsed = _parse_float(v)
            if parsed is not None and parsed > 0:
                total += parsed

        if total > 0:
            values.append((_count_label(col), total))

    if not values:
        st.info("この期間に表示できるcount記録はありません。")
        return

    values = sorted(values, key=lambda x: x[1], reverse=True)

    labels = [v[0] for v in values]
    totals = [v[1] for v in values]

    fig_height = max(4.2, min(8.0, 0.45 * len(labels) + 2.0))
    fig, ax = plt.subplots(figsize=(8.5, fig_height))
    fig.patch.set_facecolor("#ffffff")
    ax.set_facecolor("#ffffff")

    y_labels = labels[::-1]
    y_values = totals[::-1]

    ax.barh(y_labels, y_values, color="#0AA7C8")
    ax.set_xlabel("選択期間の合計")
    ax.set_ylabel("項目")

    ax.grid(True, axis="x", color=COLOR_GRID, linewidth=1, alpha=0.9)
    ax.grid(False, axis="y")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)

    for i, value in enumerate(y_values):
        ax.text(value, i, f" {value:g}", va="center", fontsize=10, weight="bold")

    fig.tight_layout()
    _show_pyplot(st, fig)


def _render_events_table(st, df: pd.DataFrame) -> None:
    st.markdown('<div class="analyst-section-title">イベント・メモ</div>', unsafe_allow_html=True)

    if df is None or df.empty:
        st.caption("表示できるイベント・メモはありません。")
        return

    d = df.copy()

    show_cols = [c for c in EVENT_COLUMNS if c in d.columns]
    if not show_cols:
        st.caption("表示できるイベント・メモ列がありません。")
        return

    d["date"] = d["_date"].dt.strftime("%Y-%m-%d")

    mask = pd.Series(False, index=d.index)
    for col in show_cols:
        if col == "date":
            continue
        mask = mask | d[col].astype(str).str.strip().ne("")

    d = d.loc[mask, show_cols].copy()

    if d.empty:
        st.caption("この期間にイベント・メモはありません。")
        return

    st.dataframe(d.tail(30), use_container_width=True, hide_index=True)


def _render_data_check(st, df: pd.DataFrame) -> None:
    with st.expander("読み取りデータを確認する", expanded=False):
        if df is None or df.empty:
            st.caption("表示できるportfolioデータがありません。")
            return

        hide_cols = ["_row_order", "_date", "_date_only"]
        show_cols = [c for c in df.columns if c not in hide_cols]
        st.dataframe(df[show_cols].tail(50), use_container_width=True, hide_index=True)


def _render_input_rule(st) -> None:
    with st.expander("Sheets入力ルール", expanded=False):
        st.markdown(
            """
- Appからは入力しません。`portfolio` シートに直接追記します。
- 50mは `run_50m_sec` に秒で入力します。旧列 `run_100m_sec` が残っていても、App側では50mとして読みます。
- 1500m・3000mは、基本は秒で入力します。例：`4:35` → `275`、`9:38` → `578`
- 誤って `4:35` の形で入っていても、このページでは秒に変換して表示します。
- 同じ日に複数行ある場合は、その日の最後の非空値を採用します。
- count系は `stretch_count`、`scanning_count`、`assist_count` など、末尾が `_count` の列を追加すると自動で集計対象になります。
"""
        )


def render_analyst_report(st, storage) -> None:
    _configure_matplotlib_font()
    _inject_analyst_css(st)

    if not hasattr(storage, "supports_portfolio") or not storage.supports_portfolio():
        st.error("現在のstorageでは Analyst Report 機能が利用できません。")
        return

    if not hasattr(storage, "load_all_portfolio"):
        st.error("storageに load_all_portfolio がありません。")
        return

    if "analyst_report_cache_version" not in st.session_state:
        st.session_state["analyst_report_cache_version"] = 0

    storage_key = _build_storage_key(storage)

    try:
        with st.spinner("Analyst Reportを読み込み中..."):
            df_portfolio = _load_portfolio_cached(
                storage,
                storage_key,
                st.session_state["analyst_report_cache_version"],
            )
    except Exception as e:
        st.error(f"Analyst Reportの読み込みに失敗しました：{e}")
        st.info("portfolioシートのヘッダー、またはGoogle Sheets APIの一時制限を確認してください。")
        return

    df_clean_all = _clean_portfolio(df_portfolio)

    _render_hero(st)

    if df_clean_all is None or df_clean_all.empty:
        st.info("portfolioシートに表示できる記録がまだありません。")
        _render_input_rule(st)
        return

    df_clean = _filter_by_period(st, df_clean_all)

    if df_clean is None or df_clean.empty:
        st.info("選択した期間に表示できる記録がありません。")
        _render_input_rule(st)
        return

    height_points = _metric_points_single(df_clean, "height_cm", "float")
    weight_points = _metric_points_single(df_clean, "weight_kg", "float")
    run50_points = _metric_points(df_clean, ["run_50m_sec", "run_100m_sec"], "seconds")
    run1500_points = _metric_points_single(df_clean, "run_1500m_sec", "seconds")
    run3000_points = _metric_points_single(df_clean, "run_3000m_sec", "seconds")

    rank_points = _metric_points_single(df_clean, "rank", "float")
    deviation_points = _metric_points_single(df_clean, "deviation", "float")
    rating_points = _metric_points_single(df_clean, "rating", "float")

    _render_latest_cards(st, height_points, weight_points, run50_points, run1500_points, run3000_points)

    st.markdown('<div class="analyst-section-title">身体</div>', unsafe_allow_html=True)
    _plot_body_chart(st, height_points, weight_points)

    st.markdown('<div class="analyst-section-title">走力・持久力</div>', unsafe_allow_html=True)

    _plot_time_chart(
        st,
        run50_points,
        "50m",
        "上がるほど速くなっています。初速・加速力の参考記録として確認します。",
        COLOR_50,
    )

    _plot_time_chart(
        st,
        run1500_points,
        "1500m",
        "上がるほど速くなっています。持久力・ペース維持力の確認に使います。",
        COLOR_1500,
    )

    _plot_time_chart(
        st,
        run3000_points,
        "3000m",
        "上がるほど速くなっています。粘り・巡航力・長い距離の安定性を確認します。",
        COLOR_3000,
    )

    st.markdown('<div class="analyst-section-title">学業</div>', unsafe_allow_html=True)

    _plot_multi_line_chart(
        st,
        df_clean,
        SCORE_COLS,
        "教科別スコア",
        "国語・数学・英語・理科・社会の点数推移です。",
        "点数",
    )

    _plot_single_metric_chart(
        st,
        rank_points,
        "順位",
        "上がるほど良い表示にするため、順位はy軸を反転しています。",
        "順位",
        COLOR_RANK,
        "rank",
        invert_y=True,
    )

    _plot_single_metric_chart(
        st,
        deviation_points,
        "偏差値",
        "偏差値の推移です。",
        "偏差値",
        COLOR_DEVIATION,
        "deviation",
        invert_y=False,
    )

    _plot_single_metric_chart(
        st,
        rating_points,
        "評点",
        "評点の推移です。",
        "評点",
        COLOR_RATING,
        "rating",
        invert_y=False,
    )

    st.markdown('<div class="analyst-section-title">行動count</div>', unsafe_allow_html=True)
    _plot_count_summary(st, df_clean)

    _render_events_table(st, df_clean)

    st.divider()

    _render_input_rule(st)
    _render_data_check(st, df_clean)

    with st.expander("Analyst Reportを更新する", expanded=False):
        st.caption("Analyst Reportは12時間キャッシュします。Sheetsを編集した直後に反映したい場合だけ再読み込みしてください。")
        if st.button("Analyst Reportを再読み込み", use_container_width=True):
            _load_portfolio_cached.clear()
            st.session_state["analyst_report_cache_version"] += 1
            st.success("Analyst Reportキャッシュをクリアしました。再読み込みします。")
            st.rerun()