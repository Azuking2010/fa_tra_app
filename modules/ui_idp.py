# file: modules/ui_idp.py
# purpose: IDPの選手用ダッシュボード画面を担当するUIモジュール。
#          Sheetsに記載されたIDP情報を読み込み、目標・マイルール・優先アクション・レビューをカード形式で表示する。

from __future__ import annotations

from datetime import date
from html import escape
from typing import Any, Optional

import pandas as pd
import streamlit as _st

from modules.common_constants import (
    calc_grade_label,
    calc_school_year_label,
    IDP_CATEGORY_LABELS,
    IDP_STATUS_LABELS,
)
from modules.ui_components import (
    display_dataframe,
    latest_row,
    score_badge,
)


IDP_CACHE_TTL_SECONDS = 60 * 60 * 12  # 12時間


# =========================
# Cached loader
# =========================
@_st.cache_data(ttl=IDP_CACHE_TTL_SECONDS, show_spinner=False)
def _load_idp_data_cached(_storage, storage_key: str, cache_version: int):
    """
    IDPデータを12時間キャッシュして読み込む。
    _storage は Streamlit cache のhash対象から外すため、先頭に underscore を付ける。

    storage_key:
        spreadsheet_id等が変わった場合にキャッシュを分けるためのキー。
    cache_version:
        手動再読み込みボタンで更新するための番号。
    """
    df_profile = _storage.load_all_idp_profile()
    df_goals = _storage.load_all_idp_goals()
    df_player = _storage.load_all_idp_player_profile()
    df_action = _storage.load_all_idp_action_plan()
    df_review = _storage.load_all_idp_review()

    return df_profile, df_goals, df_player, df_action, df_review


# =========================
# CSS
# =========================
def _inject_idp_css(st) -> None:
    st.markdown(
        """
<style>
.idp-hero {
    background: linear-gradient(135deg, #e8f7fb 0%, #ffffff 65%);
    border: 2px solid #0aa7c8;
    border-radius: 18px;
    padding: 22px 24px;
    margin: 16px 0 24px 0;
}

.idp-hero-title {
    font-size: 28px;
    font-weight: 900;
    color: #063849;
    margin-bottom: 8px;
}

.idp-hero-sub {
    font-size: 18px;
    color: #32606d;
    line-height: 1.7;
}

.idp-frame {
    position: relative;
    background: #ffffff;
    border: 3px solid #0aa7c8;
    border-radius: 18px;
    padding: 34px 28px 28px 28px;
    margin: 34px 0 36px 0;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
}

.idp-frame-label {
    position: absolute;
    top: -3px;
    left: 50%;
    transform: translateX(-50%);
    background: #0aa7c8;
    color: #ffffff;
    padding: 10px 52px 14px 52px;
    border-radius: 0 0 12px 12px;
    font-size: 24px;
    font-weight: 900;
    letter-spacing: 0.08em;
    min-width: 260px;
    text-align: center;
    white-space: nowrap;
}

.idp-frame-content {
    margin-top: 34px;
}

/* =========================
   優先アクション
   ========================= */
.idp-action-list {
    display: flex;
    flex-direction: column;
    gap: 14px;
}

.idp-action-card {
    border: 2px solid #0aa7c8;
    border-radius: 14px;
    padding: 16px 18px;
    background: #fbfeff;
}

.idp-action-title {
    color: #063849;
    font-size: 21px;
    font-weight: 900;
    margin-bottom: 10px;
}

.idp-action-main {
    margin-top: 8px;
    font-size: 17px;
    line-height: 1.7;
    color: #123f4c;
}

.idp-action-meta {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px 18px;
    margin-top: 8px;
}

.idp-action-line {
    font-size: 16px;
    line-height: 1.65;
    color: #24505d;
}

/* =========================
   目標
   ========================= */
.idp-goal-row {
    display: grid;
    grid-template-columns: 170px 1fr;
    gap: 24px;
    padding: 18px 0;
    border-bottom: 1px solid #e7eef1;
}

.idp-goal-row:last-child {
    border-bottom: none;
}

.idp-goal-side {
    color: #0aa7c8;
    font-size: 22px;
    font-weight: 900;
    line-height: 1.35;
    padding-top: 4px;
}

.idp-goal-side-small {
    display: block;
    font-size: 13px;
    font-weight: 700;
    color: #4c8796;
    margin-top: 4px;
}

.idp-goal-main {
    display: flex;
    flex-direction: column;
    gap: 12px;
}

.idp-goal-card {
    border-left: 6px solid #0aa7c8;
    background: #f7fcfe;
    border-radius: 12px;
    padding: 14px 16px;
}

.idp-goal-card.final {
    border-left-color: #f0b429;
    background: #fff9e8;
}

.idp-goal-card.long {
    border-left-color: #2563eb;
    background: #eff6ff;
}

.idp-goal-card.middle {
    border-left-color: #10b981;
    background: #ecfdf5;
}

.idp-goal-card.short {
    border-left-color: #f97316;
    background: #fff7ed;
}

.idp-goal-card.rule {
    border-left-color: #ef4444;
    background: #fff1f2;
}

.idp-goal-card.done {
    border-left-color: #f0b429;
    background: #fff8dc;
}

.idp-goal-title {
    font-size: 21px;
    font-weight: 900;
    color: #073b4c;
    margin-bottom: 6px;
}

.idp-goal-detail {
    font-size: 16px;
    color: #24505d;
    line-height: 1.65;
}

.idp-goal-meta {
    margin-top: 8px;
    font-size: 14px;
    color: #697d86;
}

/* =========================
   プレイヤープロファイル
   ========================= */
.idp-profile-layout {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 26px;
}

.idp-profile-left {
    display: flex;
    flex-direction: column;
    gap: 22px;
}

.idp-profile-block-title {
    color: #0aa7c8;
    font-size: 25px;
    font-weight: 900;
    margin-bottom: 8px;
}

.idp-profile-list {
    font-size: 17px;
    color: #114454;
    line-height: 1.85;
}

.idp-profile-card-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 18px;
}

.idp-profile-card {
    border: 2px solid #0aa7c8;
    border-radius: 12px;
    padding: 15px 16px;
    background: #ffffff;
}

.idp-profile-card-title {
    color: #0aa7c8;
    font-size: 20px;
    font-weight: 900;
    margin-bottom: 8px;
}

.idp-profile-card-item {
    color: #0a3b4d;
    font-size: 16px;
    line-height: 1.65;
    margin: 5px 0;
}

/* =========================
   アクションプラン
   PC表示：表風
   スマホ表示：PLANカード
   ========================= */
.idp-plan-desktop {
    display: block;
}

.idp-plan-mobile {
    display: none;
}

.idp-plan-table {
    display: grid;
    grid-template-columns: 1.1fr 2.3fr 1.2fr 1.1fr 1.1fr;
    gap: 10px;
}

.idp-plan-head {
    border: 2px solid #0aa7c8;
    border-radius: 8px;
    padding: 12px 10px;
    color: #0aa7c8;
    font-weight: 900;
    text-align: center;
    font-size: 17px;
}

.idp-plan-cell {
    border: 1.5px solid #0aa7c8;
    border-radius: 8px;
    padding: 10px 10px;
    color: #0a3b4d;
    font-weight: 700;
    font-size: 14px;
    line-height: 1.55;
    min-height: 46px;
}

.idp-mobile-plan-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
}

.idp-mobile-plan-card {
    border: 2px solid #0aa7c8;
    border-radius: 14px;
    padding: 16px;
    background: #fbfeff;
}

.idp-mobile-plan-title {
    font-size: 22px;
    font-weight: 900;
    color: #063849;
    margin-bottom: 12px;
}

.idp-mobile-plan-item {
    border: 1.5px solid #b9e6ef;
    border-radius: 10px;
    padding: 10px 12px;
    margin-top: 10px;
    background: #ffffff;
}

.idp-mobile-plan-label {
    font-size: 12px;
    color: #0aa7c8;
    font-weight: 900;
    letter-spacing: 0.04em;
    margin-bottom: 4px;
}

.idp-mobile-plan-value {
    font-size: 17px;
    color: #0a3b4d;
    font-weight: 800;
    line-height: 1.6;
}

/* =========================
   レビュー
   ========================= */
.idp-review-card {
    border: 2px solid #0aa7c8;
    border-radius: 16px;
    background: #fbfeff;
    padding: 18px;
    margin-bottom: 16px;
}

.idp-review-title {
    font-size: 21px;
    color: #063849;
    font-weight: 900;
    margin-bottom: 10px;
}

.idp-review-score-grid {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 10px;
    margin: 12px 0 14px 0;
}

.idp-score-box {
    background: #eefaff;
    border-radius: 10px;
    padding: 10px;
    text-align: center;
    color: #073b4c;
    font-weight: 900;
}

.idp-empty {
    color: #7b8b92;
    font-size: 15px;
    padding: 10px 0;
}

/* =========================
   Mobile
   ========================= */
@media (max-width: 900px) {
    .idp-hero {
        padding: 18px 16px;
    }

    .idp-hero-title {
        font-size: 24px;
    }

    .idp-hero-sub {
        font-size: 16px;
    }

    .idp-frame {
        padding: 38px 16px 22px 16px;
        margin: 32px 0 34px 0;
    }

    .idp-frame-label {
        min-width: 210px;
        max-width: 78%;
        padding: 9px 24px 12px 24px;
        font-size: 21px;
        letter-spacing: 0.03em;
        white-space: normal;
        line-height: 1.25;
    }

    .idp-action-meta {
        grid-template-columns: 1fr;
    }

    .idp-goal-row {
        grid-template-columns: 1fr;
        gap: 8px;
    }

    .idp-profile-layout {
        grid-template-columns: 1fr;
    }

    .idp-profile-card-grid {
        grid-template-columns: 1fr;
    }

    .idp-plan-desktop {
        display: none;
    }

    .idp-plan-mobile {
        display: block;
    }

    .idp-review-score-grid {
        grid-template-columns: 1fr 1fr;
    }
}
</style>
""",
        unsafe_allow_html=True,
    )


# =========================
# Utility
# =========================
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


def _txt(value: Any, fallback: str = "—") -> str:
    if _is_blank(value):
        return fallback
    return str(value).strip()


def _html(value: Any, fallback: str = "—") -> str:
    return escape(_txt(value, fallback))


def _norm(value: Any) -> str:
    if _is_blank(value):
        return ""
    return str(value).strip().lower()


def _ensure_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    if df is None:
        df = pd.DataFrame()
    d = df.copy()
    for c in columns:
        if c not in d.columns:
            d[c] = ""
    return d


def _build_storage_key(storage) -> str:
    """
    キャッシュの分離用キー。
    API呼び出しを増やさないため、storage.get_info() の情報だけを使う。
    """
    try:
        info = storage.get_info() or {}
    except Exception:
        info = {}

    parts = [
        str(info.get("spreadsheet_id", "")),
        str(info.get("idp_profile_worksheet", "IDP_Profile")),
        str(info.get("idp_goals_worksheet", "IDP_Goals")),
        str(info.get("idp_player_profile_worksheet", "IDP_PlayerProfile")),
        str(info.get("idp_action_plan_worksheet", "IDP_ActionPlan")),
        str(info.get("idp_review_worksheet", "IDP_Review")),
    ]
    return "|".join(parts)


def _category_label(value: Any) -> str:
    raw = _txt(value, "")
    if raw == "":
        return "—"

    local = {
        "soccer": "サッカー",
        "technical": "テクニカル",
        "physical": "フィジカル",
        "tactical": "タクティカル",
        "mental": "メンタル",
        "study": "学力",
        "english": "英語",
        "career": "進路",
        "life": "生活",
        "other": "その他",
        "テクニカル": "テクニカル",
        "フィジカル": "フィジカル",
        "タクティカル": "タクティカル",
        "メンタル": "メンタル",
        "学力": "学力",
        "進路": "進路",
    }

    key = raw.strip()
    return local.get(key, IDP_CATEGORY_LABELS.get(key, key))


def _status_label(value: Any) -> str:
    raw = _txt(value, "")
    if raw == "":
        return "—"

    local = {
        "active": "実行中",
        "done": "達成",
        "completed": "達成",
        "achieved": "達成",
        "paused": "一時停止",
        "review": "見直し中",
        "archived": "過去扱い",
        "達成": "達成",
        "完了": "達成",
        "実行中": "実行中",
    }

    key = raw.strip()
    return local.get(key, IDP_STATUS_LABELS.get(key, key))


def _is_done_status(value: Any) -> bool:
    return _norm(value) in ["done", "completed", "achieved", "達成", "完了"]


def _is_active_status(value: Any) -> bool:
    n = _norm(value)
    if n == "":
        return True
    return n in ["active", "実行中", "ongoing"]


def _priority_num(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 9999.0


def _sort_by_priority(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    d = df.copy()

    if "priority" not in d.columns:
        d["priority"] = ""

    d["_priority_num"] = d["priority"].apply(_priority_num)

    sort_cols = ["_priority_num"]
    ascending = [True]

    if "target_date" in d.columns:
        d["_target_dt"] = pd.to_datetime(d["target_date"], errors="coerce")
        sort_cols.append("_target_dt")
        ascending.append(True)

    d = d.sort_values(sort_cols, ascending=ascending, na_position="last")
    d = d.drop(columns=[c for c in ["_priority_num", "_target_dt"] if c in d.columns])
    return d.reset_index(drop=True)


def _sort_done_goals(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    d = df.copy()
    date_candidates = ["target_date", "updated_at", "created_at", "date"]

    d["_done_dt"] = pd.NaT
    for c in date_candidates:
        if c in d.columns:
            parsed = pd.to_datetime(d[c], errors="coerce")
            d["_done_dt"] = d["_done_dt"].fillna(parsed)

    d = d.sort_values("_done_dt", ascending=False, na_position="last")
    d = d.drop(columns=["_done_dt"])
    return d.reset_index(drop=True)


def _filter_goals(df_goals: pd.DataFrame, term: str, limit: Optional[int] = None) -> pd.DataFrame:
    if df_goals is None or df_goals.empty:
        return pd.DataFrame()

    d = _ensure_columns(
        df_goals,
        ["term", "status", "priority", "target_date", "goal_title", "goal_detail", "category"],
    )

    d = d[d["term"].astype(str).str.strip().str.lower() == term]

    if d.empty:
        return pd.DataFrame()

    d = d[d["status"].apply(lambda x: not _is_done_status(x))]
    d = d[d["status"].apply(_is_active_status)]

    d = _sort_by_priority(d)

    if limit is not None:
        d = d.head(limit)

    return d.reset_index(drop=True)


def _render_html(st, html: str) -> None:
    st.markdown(html, unsafe_allow_html=True)


def _frame_start(title: str) -> str:
    return f"""
<div class="idp-frame">
  <div class="idp-frame-label">{escape(title)}</div>
  <div class="idp-frame-content">
"""


def _frame_end() -> str:
    return """
  </div>
</div>
"""


# =========================
# Header
# =========================
def _render_header(st, df_profile: pd.DataFrame) -> None:
    row = latest_row(df_profile)

    auto_grade = calc_grade_label(date.today())
    auto_school_year = calc_school_year_label(date.today())

    main_position = _txt(row.get("main_position"))
    sub_position_1 = _txt(row.get("sub_position_1"))
    sub_position_2 = _txt(row.get("sub_position_2"))
    option_position = _txt(row.get("option_position"))

    position_text = " / ".join(
        [x for x in [main_position, sub_position_1, sub_position_2, option_position] if x != "—"]
    )
    if not position_text:
        position_text = "—"

    height = _txt(row.get("height_cm"))
    weight = _txt(row.get("weight_kg"))
    foot = _txt(row.get("dominant_foot"))
    team = _txt(row.get("team"))
    player_type = _txt(row.get("player_type"))

    _render_html(
        st,
        f"""
<div class="idp-hero">
  <div class="idp-hero-title">IDP｜個別育成プラン</div>
  <div class="idp-hero-sub">
    このページは編集画面ではなく、選手本人が見るダッシュボードです。<br>
    目標・今月やること・自分の強みと課題を確認します。
  </div>
  <div style="margin-top:16px; display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:10px;">
    <div><b>学年</b><br>{escape(auto_grade)}</div>
    <div><b>年度</b><br>{escape(auto_school_year)}</div>
    <div><b>身長 / 体重</b><br>{escape(height)} cm / {escape(weight)} kg</div>
    <div><b>利き足</b><br>{escape(foot)}</div>
  </div>
  <div style="margin-top:12px; display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:10px;">
    <div><b>所属</b><br>{escape(team)}</div>
    <div><b>ポジション</b><br>{escape(position_text)}</div>
    <div><b>タイプ</b><br>{escape(player_type)}</div>
  </div>
</div>
""",
    )


# =========================
# Priority Action
# =========================
def _render_priority_actions(st, df_action: pd.DataFrame) -> None:
    if df_action is None or df_action.empty:
        actions = pd.DataFrame()
    else:
        actions = _ensure_columns(
            df_action,
            [
                "priority",
                "theme",
                "category",
                "issue",
                "action",
                "frequency",
                "related_training",
                "target_period",
                "status",
            ],
        )
        actions = actions[actions["status"].apply(_is_active_status)]
        actions = _sort_by_priority(actions).head(5)

    if actions.empty:
        body = '<div class="idp-empty">今月の優先アクションはまだ設定されていません。</div>'
    else:
        cards = []
        for _, row in actions.iterrows():
            priority = _html(row.get("priority"))
            theme = _html(row.get("theme"))
            category = escape(_category_label(row.get("category")))
            issue = _html(row.get("issue"))
            action = _html(row.get("action"))
            frequency = _html(row.get("frequency"))
            related = _html(row.get("related_training"))
            target = _html(row.get("target_period"))

            cards.append(
                f"""
<div class="idp-action-card">
  <div class="idp-action-title">優先{priority}｜{theme}</div>
  <div class="idp-action-main"><b>行動：</b>{action}</div>
  <div class="idp-action-meta">
    <div class="idp-action-line"><b>カテゴリ：</b>{category}</div>
    <div class="idp-action-line"><b>頻度：</b>{frequency}</div>
    <div class="idp-action-line"><b>課題：</b>{issue}</div>
    <div class="idp-action-line"><b>関連：</b>{related}</div>
    <div class="idp-action-line"><b>期間：</b>{target}</div>
  </div>
</div>
"""
            )
        body = f'<div class="idp-action-list">{"".join(cards)}</div>'

    _render_html(st, _frame_start("今月の優先アクション") + body + _frame_end())


# =========================
# Goals
# =========================
def _goal_card(row: pd.Series, css_class: str = "") -> str:
    title = _html(row.get("goal_title"))
    detail = _html(row.get("goal_detail"), "")
    target_date = _txt(row.get("target_date"), "")
    category = _category_label(row.get("category"))
    priority = _txt(row.get("priority"), "")

    meta_parts = []
    if priority not in ["", "—"]:
        meta_parts.append(f"優先：{escape(priority)}")
    if category not in ["", "—"]:
        meta_parts.append(f"カテゴリ：{escape(category)}")
    if target_date not in ["", "—"]:
        meta_parts.append(f"期限：{escape(target_date)}")

    meta_html = ""
    if meta_parts:
        meta_html = f'<div class="idp-goal-meta">{"　|　".join(meta_parts)}</div>'

    detail_html = ""
    if detail:
        detail_html = f'<div class="idp-goal-detail">{detail}</div>'

    return f"""
<div class="idp-goal-card {css_class}">
  <div class="idp-goal-title">{title}</div>
  {detail_html}
  {meta_html}
</div>
"""


def _goal_section_html(side_title: str, rows: pd.DataFrame, css_class: str, side_small: str = "") -> str:
    small = f'<span class="idp-goal-side-small">{escape(side_small)}</span>' if side_small else ""

    if rows is None or rows.empty:
        cards = '<div class="idp-empty">まだ設定されていません。</div>'
    else:
        cards = "".join(_goal_card(row, css_class) for _, row in rows.iterrows())

    return f"""
<div class="idp-goal-row">
  <div class="idp-goal-side">{escape(side_title)}{small}</div>
  <div class="idp-goal-main">{cards}</div>
</div>
"""


def _render_goals_dashboard(st, df_goals: pd.DataFrame) -> None:
    if df_goals is None or df_goals.empty:
        _render_html(
            st,
            _frame_start("目標")
            + '<div class="idp-empty">IDP_Goals にデータがありません。</div>'
            + _frame_end(),
        )
        return

    df_goals = _ensure_columns(
        df_goals,
        ["term", "status", "priority", "target_date", "goal_title", "goal_detail", "category"],
    )

    final_goals = _filter_goals(df_goals, "final", limit=1)
    long_goals = _filter_goals(df_goals, "long", limit=2)
    middle_goals = _filter_goals(df_goals, "middle", limit=3)
    short_goals = _filter_goals(df_goals, "short", limit=10)
    my_rules = _filter_goals(df_goals, "my_rule", limit=5)

    done_goals = df_goals[df_goals["status"].apply(_is_done_status)].copy()
    done_goals = _sort_done_goals(done_goals).head(5)

    html = _frame_start("目標")
    html += _goal_section_html("🌟 最終目標", final_goals, "final", "北極星")
    html += _goal_section_html("🎯 長期", long_goals, "long", "プロへの道")
    html += _goal_section_html("🧭 中期", middle_goals, "middle", "1〜2年")
    html += _goal_section_html("📌 短期", short_goals, "short", "今月〜半年")
    html += _goal_section_html("🔥 マイルール", my_rules, "rule", "常に守る基準")
    html += _goal_section_html("👑 達成目標", done_goals, "done", "直近5個")
    html += _frame_end()

    _render_html(st, html)


# =========================
# Player Profile
# =========================
def _rows_by_type(df: pd.DataFrame, type_name: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    d = _ensure_columns(df, ["type", "priority", "category", "item", "detail"])

    targets = {
        "strength": ["strength", "強み"],
        "weakness": ["weakness", "課題"],
        "feature": ["feature", "特徴"],
        "risk": ["risk", "注意", "注意点"],
    }.get(type_name, [type_name])

    d["_type_norm"] = d["type"].astype(str).str.strip().str.lower()
    target_norm = [str(x).strip().lower() for x in targets]
    d = d[d["_type_norm"].isin(target_norm)]
    d = d.drop(columns=["_type_norm"])
    d = _sort_by_priority(d)
    return d.reset_index(drop=True)


def _simple_profile_list(rows: pd.DataFrame, limit: int = 6) -> str:
    if rows is None or rows.empty:
        return '<div class="idp-empty">未設定</div>'

    items = []
    for _, row in rows.head(limit).iterrows():
        item = _html(row.get("item"))
        detail = _html(row.get("detail"), "")
        if detail and detail != "—":
            items.append(f"<div>・<b>{item}</b><br><span style='font-size:14px;'>{detail}</span></div>")
        else:
            items.append(f"<div>・<b>{item}</b></div>")
    return "".join(items)


def _category_profile_cards(df_player: pd.DataFrame) -> str:
    if df_player is None or df_player.empty:
        return '<div class="idp-empty">未設定</div>'

    d = _ensure_columns(df_player, ["category", "priority", "item", "detail"])

    preferred = [
        "technical",
        "テクニカル",
        "physical",
        "フィジカル",
        "tactical",
        "タクティカル",
        "mental",
        "メンタル",
    ]

    cards = []
    used_indexes = set()

    for cat in preferred:
        sub = d[d["category"].astype(str).str.strip().str.lower() == str(cat).strip().lower()]
        if sub.empty:
            continue

        used_indexes.update(sub.index.tolist())
        label = _category_label(cat)

        lines = []
        for _, row in _sort_by_priority(sub).head(5).iterrows():
            item = _html(row.get("item"))
            detail = _html(row.get("detail"), "")
            if detail and detail != "—":
                lines.append(
                    f"<div class='idp-profile-card-item'>✓ <b>{item}</b><br><span style='font-size:14px;'>{detail}</span></div>"
                )
            else:
                lines.append(f"<div class='idp-profile-card-item'>✓ <b>{item}</b></div>")

        cards.append(
            f"""
<div class="idp-profile-card">
  <div class="idp-profile-card-title">● {escape(label)}</div>
  {''.join(lines)}
</div>
"""
        )

    rest = d[~d.index.isin(used_indexes)]
    if not rest.empty:
        lines = []
        for _, row in _sort_by_priority(rest).head(6).iterrows():
            item = _html(row.get("item"))
            detail = _html(row.get("detail"), "")
            if detail and detail != "—":
                lines.append(
                    f"<div class='idp-profile-card-item'>✓ <b>{item}</b><br><span style='font-size:14px;'>{detail}</span></div>"
                )
            else:
                lines.append(f"<div class='idp-profile-card-item'>✓ <b>{item}</b></div>")

        cards.append(
            f"""
<div class="idp-profile-card">
  <div class="idp-profile-card-title">● その他</div>
  {''.join(lines)}
</div>
"""
        )

    if not cards:
        return '<div class="idp-empty">未設定</div>'

    return f'<div class="idp-profile-card-grid">{"".join(cards)}</div>'


def _render_player_profile(st, df_player: pd.DataFrame) -> None:
    strengths = _rows_by_type(df_player, "strength")
    weaknesses = _rows_by_type(df_player, "weakness")

    html = _frame_start("プレイヤープロファイル")
    html += f"""
<div class="idp-profile-layout">
  <div class="idp-profile-left">
    <div>
      <div class="idp-profile-block-title">強み</div>
      <div class="idp-profile-list">{_simple_profile_list(strengths)}</div>
    </div>
    <div>
      <div class="idp-profile-block-title">課題</div>
      <div class="idp-profile-list">{_simple_profile_list(weaknesses)}</div>
    </div>
  </div>
  <div>
    {_category_profile_cards(df_player)}
  </div>
</div>
"""
    html += _frame_end()
    _render_html(st, html)


# =========================
# Action Plan List
# =========================
def _render_action_plan_table(st, df_action: pd.DataFrame) -> None:
    if df_action is None or df_action.empty:
        body = '<div class="idp-empty">IDP_ActionPlan にデータがありません。</div>'
    else:
        d = _ensure_columns(
            df_action,
            ["theme", "action", "who", "frequency", "target_period", "priority"],
        )
        d = _sort_by_priority(d).head(12)

        desktop_header = """
<div class="idp-plan-desktop">
  <div class="idp-plan-table">
    <div class="idp-plan-head">何を</div>
    <div class="idp-plan-head">どのように</div>
    <div class="idp-plan-head">誰が</div>
    <div class="idp-plan-head">頻度</div>
    <div class="idp-plan-head">いつまでに</div>
"""
        desktop_cells = []

        mobile_cards = ['<div class="idp-plan-mobile"><div class="idp-mobile-plan-list">']

        for idx, (_, row) in enumerate(d.iterrows(), start=1):
            priority_raw = _txt(row.get("priority"), "")
            plan_no = priority_raw if priority_raw not in ["", "—"] else str(idx)

            what = _html(row.get("theme"))
            how = _html(row.get("action"))
            who = _html(row.get("who"), "自分")
            frequency = _html(row.get("frequency"))
            target = _html(row.get("target_period"))

            desktop_cells.append(f'<div class="idp-plan-cell">{what}</div>')
            desktop_cells.append(f'<div class="idp-plan-cell">{how}</div>')
            desktop_cells.append(f'<div class="idp-plan-cell">{who}</div>')
            desktop_cells.append(f'<div class="idp-plan-cell">{frequency}</div>')
            desktop_cells.append(f'<div class="idp-plan-cell">{target}</div>')

            mobile_cards.append(
                f"""
<div class="idp-mobile-plan-card">
  <div class="idp-mobile-plan-title">PLAN {escape(plan_no)}</div>

  <div class="idp-mobile-plan-item">
    <div class="idp-mobile-plan-label">What</div>
    <div class="idp-mobile-plan-value">{what}</div>
  </div>

  <div class="idp-mobile-plan-item">
    <div class="idp-mobile-plan-label">How</div>
    <div class="idp-mobile-plan-value">{how}</div>
  </div>

  <div class="idp-mobile-plan-item">
    <div class="idp-mobile-plan-label">Who</div>
    <div class="idp-mobile-plan-value">{who}</div>
  </div>

  <div class="idp-mobile-plan-item">
    <div class="idp-mobile-plan-label">Frequency</div>
    <div class="idp-mobile-plan-value">{frequency}</div>
  </div>

  <div class="idp-mobile-plan-item">
    <div class="idp-mobile-plan-label">Until</div>
    <div class="idp-mobile-plan-value">{target}</div>
  </div>
</div>
"""
            )

        desktop_html = desktop_header + "".join(desktop_cells) + """
  </div>
</div>
"""
        mobile_html = "".join(mobile_cards) + """
</div></div>
"""
        body = desktop_html + mobile_html

    _render_html(st, _frame_start("アクションプラン") + body + _frame_end())


# =========================
# Review
# =========================
def _sort_reviews(df_review: pd.DataFrame) -> pd.DataFrame:
    if df_review is None or df_review.empty:
        return pd.DataFrame()

    d = _ensure_columns(df_review, ["review_month", "review_date", "priority"])

    d["_review_dt"] = pd.to_datetime(d["review_month"].astype(str) + "-01", errors="coerce")
    fallback_dt = pd.to_datetime(d["review_date"], errors="coerce")
    d["_review_dt"] = d["_review_dt"].fillna(fallback_dt)
    d["_priority_num"] = d["priority"].apply(_priority_num)

    d = d.sort_values(["_review_dt", "_priority_num"], ascending=[False, True], na_position="last")
    d = d.drop(columns=["_review_dt", "_priority_num"])
    return d.reset_index(drop=True)


def _review_card(row: pd.Series) -> str:
    month = _html(row.get("review_month"))
    theme = _html(row.get("theme"))
    priority = _html(row.get("priority"))
    category = escape(_category_label(row.get("category")))

    execution = escape(score_badge(row.get("execution_score")))
    awareness = escape(score_badge(row.get("awareness_score")))
    change = escape(score_badge(row.get("change_score")))
    overall = escape(score_badge(row.get("overall_score")))

    continue_decision = _html(row.get("continue_decision"))
    next_priority = _html(row.get("next_priority"))
    good = _html(row.get("good_point"), "")
    issue = _html(row.get("issue"), "")
    next_action = _html(row.get("next_action"), "")
    pep = _html(row.get("pep_comment"), "")

    lines = []
    if good:
        lines.append(f"<div><b>できたこと：</b>{good}</div>")
    if issue:
        lines.append(f"<div><b>課題：</b>{issue}</div>")
    if next_action:
        lines.append(f"<div><b>次にやること：</b>{next_action}</div>")
    if pep:
        lines.append(f"<div><b>Pepコメント：</b>{pep}</div>")

    optional = "".join(lines) if lines else '<div class="idp-empty">テキストメモは未入力です。</div>'

    return f"""
<div class="idp-review-card">
  <div class="idp-review-title">{month}｜優先{priority}｜{theme}</div>
  <div style="color:#607680; font-size:14px;">カテゴリ：{category}</div>
  <div class="idp-review-score-grid">
    <div class="idp-score-box">実行<br>{execution}</div>
    <div class="idp-score-box">意識<br>{awareness}</div>
    <div class="idp-score-box">変化<br>{change}</div>
    <div class="idp-score-box">総合<br>{overall}</div>
  </div>
  <div style="font-size:15px; line-height:1.75; color:#24505d;">
    <div><b>来月判断：</b>{continue_decision}</div>
    <div><b>次の優先度：</b>{next_priority}</div>
    {optional}
  </div>
</div>
"""


def _render_reviews(st, df_review: pd.DataFrame) -> None:
    if df_review is None or df_review.empty:
        _render_html(
            st,
            _frame_start("レビュー")
            + '<div class="idp-empty">IDP_Review にデータがありません。</div>'
            + _frame_end(),
        )
        return

    d = _sort_reviews(df_review)

    latest_month = None
    if "review_month" in d.columns and not d.empty:
        latest_month = _txt(d.iloc[0].get("review_month"), "")

    if latest_month:
        latest = d[d["review_month"].astype(str).str.strip() == latest_month]
        past = d[d["review_month"].astype(str).str.strip() != latest_month]
    else:
        latest = d.head(3)
        past = d.iloc[3:]

    latest_html = "".join(_review_card(row) for _, row in latest.iterrows())

    _render_html(st, _frame_start("最新レビュー") + latest_html + _frame_end())

    if not past.empty:
        with st.expander("過去レビューを見る", expanded=False):
            past_html = "".join(_review_card(row) for _, row in past.iterrows())
            _render_html(st, past_html)


# =========================
# Main
# =========================
def render_idp(st, storage) -> None:
    _inject_idp_css(st)

    if not hasattr(storage, "supports_idp") or not storage.supports_idp():
        st.error("現在のstorageではIDP機能が利用できません。")
        return

    if "idp_cache_version" not in st.session_state:
        st.session_state["idp_cache_version"] = 0

    with st.expander("IDPデータ更新", expanded=False):
        st.caption("IDPは12時間キャッシュします。Sheetsを編集した直後に反映したい場合だけ再読み込みしてください。")
        if st.button("IDPデータを再読み込み", use_container_width=True):
            _load_idp_data_cached.clear()
            st.session_state["idp_cache_version"] += 1
            st.success("IDPキャッシュをクリアしました。再読み込みします。")
            st.rerun()

    storage_key = _build_storage_key(storage)

    try:
        with st.spinner("IDPデータを読み込み中..."):
            df_profile, df_goals, df_player, df_action, df_review = _load_idp_data_cached(
                storage,
                storage_key,
                st.session_state["idp_cache_version"],
            )
    except Exception as e:
        st.error(f"IDPデータの読み込みに失敗しました：{e}")
        st.info("短時間に何度も開いた場合は、Google Sheets APIの一時制限に当たることがあります。少し時間を置くか、後ほど再読み込みしてください。")
        return

    st.caption("IDPデータ：12時間キャッシュ中")

    _render_header(st, df_profile)
    _render_priority_actions(st, df_action)
    _render_goals_dashboard(st, df_goals)
    _render_player_profile(st, df_player)
    _render_action_plan_table(st, df_action)
    _render_reviews(st, df_review)

    with st.expander("Sheetsの元データを確認する", expanded=False):
        st.markdown("### IDP_Profile")
        display_dataframe(st, df_profile, height=200)

        st.markdown("### IDP_Goals")
        display_dataframe(st, df_goals, height=260)

        st.markdown("### IDP_PlayerProfile")
        display_dataframe(st, df_player, height=260)

        st.markdown("### IDP_ActionPlan")
        display_dataframe(st, df_action, height=260)

        st.markdown("### IDP_Review")
        display_dataframe(st, df_review, height=260)