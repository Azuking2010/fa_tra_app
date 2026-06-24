# file: modules/ui_pep_review.py
# purpose: IDP_Reviewに保存されたPepサマリーを表示するTrainer Review画面。
#          review_type=monthly_summary / status=active の行だけを対象にし、
#          直近2回を常時表示、過去分は月選択で表示する。

from __future__ import annotations

from html import escape
from typing import Any

import pandas as pd
import streamlit as _st


REVIEW_CACHE_TTL_SECONDS = 60 * 60 * 12  # 12時間


REVIEW_COLUMNS = [
    "review_id",
    "review_month",
    "review_date",
    "review_type",
    "period_start",
    "period_end",
    "source_type",
    "source_ids",
    "related_goal_id",
    "related_action_id",
    "theme",
    "category",
    "theme_tags",
    "priority",
    "achievement_type",
    "achievement_value",
    "match_context",
    "review_title",
    "review_body",
    "next_one",
    "light_counts",
    "good_point",
    "issue",
    "next_action",
    "evidence_text",
    "parent_comment",
    "pep_comment",
    "status",
    "created_at",
    "updated_at",
]


@_st.cache_data(ttl=REVIEW_CACHE_TTL_SECONDS, show_spinner=False)
def _load_review_data_cached(_storage, storage_key: str, cache_version: int) -> pd.DataFrame:
    """
    IDP_Reviewを12時間キャッシュして読み込む。
    _storage は Streamlit cache のhash対象から外すため、先頭に underscore を付ける。
    """
    return _storage.load_all_idp_review()


def _inject_review_css(st) -> None:
    st.markdown(
        """
<style>
.pep-review-hero {
    background: linear-gradient(135deg, #f7fbff 0%, #ffffff 70%);
    border: 2px solid #0aa7c8;
    border-radius: 18px;
    padding: 22px 24px;
    margin: 16px 0 24px 0;
}

.pep-review-hero-title {
    font-size: 30px;
    font-weight: 900;
    color: #063849;
    margin-bottom: 8px;
}

.pep-review-hero-sub {
    font-size: 17px;
    color: #32606d;
    line-height: 1.7;
}

.pep-review-section-title {
    font-size: 25px;
    font-weight: 900;
    color: #063849;
    margin: 28px 0 14px 0;
}

.pep-review-card {
    background: #ffffff;
    border: 2px solid #0aa7c8;
    border-radius: 18px;
    padding: 22px 24px;
    margin: 18px 0 24px 0;
    box-shadow: 0 6px 18px rgba(0, 0, 0, 0.05);
}

.pep-review-card.recent {
    border-width: 3px;
}

.pep-review-title {
    font-size: 24px;
    font-weight: 900;
    color: #063849;
    margin-bottom: 8px;
    line-height: 1.4;
}

.pep-review-period {
    display: inline-block;
    background: #e8f7fb;
    color: #095165;
    border-radius: 999px;
    padding: 6px 14px;
    font-size: 15px;
    font-weight: 800;
    margin: 4px 0 18px 0;
}

.pep-review-body {
    font-size: 17px;
    color: #123f4c;
    line-height: 1.9;
    white-space: pre-wrap;
    margin-top: 8px;
}

.pep-review-next {
    background: #fff9e8;
    border-left: 6px solid #f0b429;
    border-radius: 12px;
    padding: 14px 16px;
    margin-top: 20px;
}

.pep-review-next-label {
    color: #7a4b00;
    font-size: 15px;
    font-weight: 900;
    margin-bottom: 6px;
}

.pep-review-next-text {
    color: #4b3400;
    font-size: 18px;
    font-weight: 800;
    line-height: 1.7;
}

.pep-review-counts {
    background: #f7fcfe;
    border: 1.5px solid #b9e6ef;
    border-radius: 12px;
    padding: 12px 14px;
    margin-top: 16px;
    color: #24505d;
    font-size: 15px;
    line-height: 1.7;
}

.pep-review-counts-label {
    color: #0aa7c8;
    font-weight: 900;
    margin-bottom: 4px;
}

.pep-review-empty {
    color: #7b8b92;
    font-size: 16px;
    padding: 10px 0;
}

@media (max-width: 900px) {
    .pep-review-hero {
        padding: 18px 16px;
    }

    .pep-review-hero-title {
        font-size: 25px;
    }

    .pep-review-hero-sub {
        font-size: 16px;
    }

    .pep-review-card {
        padding: 18px 16px;
    }

    .pep-review-title {
        font-size: 22px;
    }

    .pep-review-body {
        font-size: 16px;
    }

    .pep-review-next-text {
        font-size: 17px;
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


def _html(value: Any, fallback: str = "") -> str:
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
    try:
        info = storage.get_info() or {}
    except Exception:
        info = {}

    parts = [
        str(info.get("spreadsheet_id", "")),
        str(info.get("idp_review_worksheet", "IDP_Review")),
    ]
    return "|".join(parts)


def _is_active_monthly_summary(row: pd.Series) -> bool:
    review_type = _norm(row.get("review_type"))
    status = _norm(row.get("status"))

    if review_type != "monthly_summary":
        return False

    if status == "":
        return True

    return status == "active"


def _prepare_reviews(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=REVIEW_COLUMNS)

    d = _ensure_columns(df, REVIEW_COLUMNS)
    d = d[d.apply(_is_active_monthly_summary, axis=1)].copy()

    if d.empty:
        return pd.DataFrame(columns=REVIEW_COLUMNS)

    d["_period_end_dt"] = pd.to_datetime(d["period_end"], errors="coerce")
    d["_review_date_dt"] = pd.to_datetime(d["review_date"], errors="coerce")
    d["_updated_at_dt"] = pd.to_datetime(d["updated_at"], errors="coerce")

    d = d.sort_values(
        ["_period_end_dt", "_review_date_dt", "_updated_at_dt", "review_id"],
        ascending=[False, False, False, False],
        na_position="last",
    )

    d = d.drop(columns=[c for c in ["_period_end_dt", "_review_date_dt", "_updated_at_dt"] if c in d.columns])
    return d.reset_index(drop=True)


def _period_label(row: pd.Series) -> str:
    start = _txt(row.get("period_start"), "")
    end = _txt(row.get("period_end"), "")
    month = _txt(row.get("review_month"), "")

    if start and end:
        return f"{start} 〜 {end}"

    if month:
        return month

    return "対象期間未設定"


def _render_hero(st) -> None:
    st.markdown(
        """
<div class="pep-review-hero">
  <div class="pep-review-hero-title">🏋️ Trainer Review</div>
  <div class="pep-review-hero-sub">
    Pepからの振り返りです。直近2回のレビューを確認し、次に意識することを1つに絞ります。
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def _render_review_card(st, row: pd.Series, recent: bool = False) -> None:
    title = _html(row.get("review_title"), "Trainer Review")
    period = escape(_period_label(row))
    body = _html(row.get("review_body"), "")
    next_one = _html(row.get("next_one"), "")
    light_counts = _html(row.get("light_counts"), "")

    card_class = "pep-review-card recent" if recent else "pep-review-card"

    next_html = ""
    if next_one:
        next_html = f"""
<div class="pep-review-next">
  <div class="pep-review-next-label">次の1つ</div>
  <div class="pep-review-next-text">{next_one}</div>
</div>
"""

    counts_html = ""
    if light_counts:
        counts_html = f"""
<div class="pep-review-counts">
  <div class="pep-review-counts-label">記録カウント</div>
  <div>{light_counts}</div>
</div>
"""

    if not body:
        body = "レビュー本文が未入力です。"

    st.markdown(
        f"""
<div class="{card_class}">
  <div class="pep-review-title">{title}</div>
  <div class="pep-review-period">{period}</div>
  <div class="pep-review-body">{body}</div>
  {next_html}
  {counts_html}
</div>
""",
        unsafe_allow_html=True,
    )


def _render_recent_reviews(st, df_reviews: pd.DataFrame) -> pd.DataFrame:
    st.markdown('<div class="pep-review-section-title">直近のレビュー</div>', unsafe_allow_html=True)

    if df_reviews is None or df_reviews.empty:
        st.info("表示できるTrainer Reviewはまだありません。")
        return pd.DataFrame(columns=REVIEW_COLUMNS)

    recent = df_reviews.head(2).copy()

    for _, row in recent.iterrows():
        _render_review_card(st, row, recent=True)

    older = df_reviews.iloc[2:].copy()
    return older.reset_index(drop=True)


def _render_archive_reviews(st, older_reviews: pd.DataFrame) -> None:
    st.markdown('<div class="pep-review-section-title">過去のレビュー</div>', unsafe_allow_html=True)

    if older_reviews is None or older_reviews.empty:
        st.caption("過去レビューはまだありません。")
        return

    d = _ensure_columns(older_reviews, REVIEW_COLUMNS)

    month_values = []
    for value in d["review_month"].tolist():
        month = _txt(value, "")
        if month and month not in month_values:
            month_values.append(month)

    if not month_values:
        st.caption("月選択できる過去レビューはまだありません。")
        return

    selected_month = st.selectbox(
        "月を選択",
        month_values,
        index=0,
        key="pep_review_archive_month",
    )

    month_reviews = d[d["review_month"].astype(str).str.strip() == selected_month].copy()

    if month_reviews.empty:
        st.caption("選択した月のレビューはありません。")
        return

    for _, row in month_reviews.iterrows():
        _render_review_card(st, row, recent=False)


def render_pep_review(st, storage) -> None:
    _inject_review_css(st)

    if not hasattr(storage, "supports_idp") or not storage.supports_idp():
        st.error("現在のstorageでは Trainer Review 機能が利用できません。")
        return

    if not hasattr(storage, "load_all_idp_review"):
        st.error("storageに load_all_idp_review がありません。")
        return

    if "pep_review_cache_version" not in st.session_state:
        st.session_state["pep_review_cache_version"] = 0

    storage_key = _build_storage_key(storage)

    try:
        with st.spinner("Trainer Reviewを読み込み中..."):
            df_review = _load_review_data_cached(
                storage,
                storage_key,
                st.session_state["pep_review_cache_version"],
            )
    except Exception as e:
        st.error(f"Trainer Reviewの読み込みに失敗しました：{e}")
        st.info("IDP_Reviewシートのヘッダー、またはGoogle Sheets APIの一時制限を確認してください。")
        return

    df_reviews = _prepare_reviews(df_review)

    _render_hero(st)

    older_reviews = _render_recent_reviews(st, df_reviews)

    st.divider()

    with st.expander("過去レビューを見る", expanded=False):
        _render_archive_reviews(st, older_reviews)

    with st.expander("Trainer Reviewを更新する", expanded=False):
        st.caption("Trainer Reviewは12時間キャッシュします。Sheetsを編集した直後に反映したい場合だけ再読み込みしてください。")
        if st.button("Trainer Reviewを再読み込み", use_container_width=True):
            _load_review_data_cached.clear()
            st.session_state["pep_review_cache_version"] += 1
            st.success("Trainer Reviewキャッシュをクリアしました。再読み込みします。")
            st.rerun()