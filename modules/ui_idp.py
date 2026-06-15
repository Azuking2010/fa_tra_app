# file: modules/ui_idp.py
# purpose: IDPの表示画面を担当するUIモジュール。
#          IDP_Profile / Goals / PlayerProfile / ActionPlan / Review をSheetsから読み込み、縦スクロールで表示する。

from __future__ import annotations

from datetime import date

import pandas as pd

from modules.common_constants import (
    calc_grade_label,
    calc_school_year_label,
    IDP_CATEGORY_LABELS,
    IDP_STATUS_LABELS,
)
from modules.ui_components import (
    display_dataframe,
    join_non_empty,
    latest_row,
    safe_text,
    score_badge,
    section_title,
)


def _rename_columns(df: pd.DataFrame, mapping: dict[str, str]) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    cols = {c: mapping.get(c, c) for c in df.columns}
    return df.rename(columns=cols)


def _category_label(value) -> str:
    if value is None:
        return "—"
    key = str(value).strip()
    if key == "":
        return "—"
    return IDP_CATEGORY_LABELS.get(key, key)


def _status_label(value) -> str:
    if value is None:
        return "—"
    key = str(value).strip()
    if key == "":
        return "—"
    return IDP_STATUS_LABELS.get(key, key)


def _render_profile(st, df_profile: pd.DataFrame) -> None:
    section_title(
        st,
        "① プロフィール",
        "学年・年度は4月基準でアプリ側が自動計算します。",
    )

    row = latest_row(df_profile)

    auto_grade = calc_grade_label(date.today())
    auto_school_year = calc_school_year_label(date.today())

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("学年", auto_grade)
    c2.metric("年度", auto_school_year)
    c3.metric("身長", f"{safe_text(row.get('height_cm'))} cm")
    c4.metric("体重", f"{safe_text(row.get('weight_kg'))} kg")

    st.markdown("### ポジション")
    p1, p2, p3, p4 = st.columns(4)
    p1.metric("メイン", safe_text(row.get("main_position")))
    p2.metric("サブ1", safe_text(row.get("sub_position_1")))
    p3.metric("サブ2", safe_text(row.get("sub_position_2")))
    p4.metric("オプション", safe_text(row.get("option_position")))

    st.markdown("### 基本情報")
    b1, b2, b3 = st.columns(3)
    b1.metric("利き足", safe_text(row.get("dominant_foot")))
    b2.metric("所属", safe_text(row.get("team")))
    b3.metric("タイプ", safe_text(row.get("player_type")))

    note = safe_text(row.get("note"))
    if note != "—":
        st.info(note)

    with st.expander("IDP_Profile シート内容を確認する", expanded=False):
        display_dataframe(st, df_profile, height=220)


def _render_goals(st, df_goals: pd.DataFrame) -> None:
    section_title(st, "② 目標", "長期・中期・短期・日常目標を確認します。")

    if df_goals is None or df_goals.empty:
        st.info("IDP_Goals にデータがありません。")
        return

    df = df_goals.copy()

    if "priority" in df.columns:
        df["priority_num"] = pd.to_numeric(df["priority"], errors="coerce")
        df = df.sort_values(["priority_num"], ascending=True, na_position="last")
        df = df.drop(columns=["priority_num"])

    show_cols = [
        "priority",
        "term",
        "category",
        "goal_title",
        "goal_detail",
        "target_date",
        "status",
        "note",
    ]
    show_cols = [c for c in show_cols if c in df.columns]

    out = df[show_cols].copy()
    if "category" in out.columns:
        out["category"] = out["category"].apply(_category_label)
    if "status" in out.columns:
        out["status"] = out["status"].apply(_status_label)

    out = _rename_columns(
        out,
        {
            "priority": "優先",
            "term": "期間",
            "category": "カテゴリ",
            "goal_title": "目標",
            "goal_detail": "詳細",
            "target_date": "期限",
            "status": "状態",
            "note": "メモ",
        },
    )

    display_dataframe(st, out, height=300)


def _render_player_profile(st, df_player: pd.DataFrame) -> None:
    section_title(st, "③ プレイヤープロファイル", "強み・課題・特徴を確認します。")

    if df_player is None or df_player.empty:
        st.info("IDP_PlayerProfile にデータがありません。")
        return

    df = df_player.copy()

    if "priority" in df.columns:
        df["priority_num"] = pd.to_numeric(df["priority"], errors="coerce")
        df = df.sort_values(["type", "priority_num"], ascending=[True, True], na_position="last")
        df = df.drop(columns=["priority_num"])

    show_cols = [
        "type",
        "priority",
        "category",
        "item",
        "detail",
        "level",
        "status",
        "note",
    ]
    show_cols = [c for c in show_cols if c in df.columns]

    out = df[show_cols].copy()
    if "category" in out.columns:
        out["category"] = out["category"].apply(_category_label)
    if "status" in out.columns:
        out["status"] = out["status"].apply(_status_label)

    type_labels = {
        "strength": "強み",
        "weakness": "課題",
        "feature": "特徴",
        "risk": "注意",
    }
    if "type" in out.columns:
        out["type"] = out["type"].apply(lambda x: type_labels.get(str(x).strip(), str(x)))

    out = _rename_columns(
        out,
        {
            "type": "種別",
            "priority": "優先",
            "category": "カテゴリ",
            "item": "項目",
            "detail": "詳細",
            "level": "レベル",
            "status": "状態",
            "note": "メモ",
        },
    )

    display_dataframe(st, out, height=360)


def _render_action_plan(st, df_action: pd.DataFrame) -> None:
    section_title(st, "④ アクションプラン", "課題を具体的な行動に落とし込む場所です。")

    if df_action is None or df_action.empty:
        st.info("IDP_ActionPlan にデータがありません。")
        return

    df = df_action.copy()

    if "priority" in df.columns:
        df["priority_num"] = pd.to_numeric(df["priority"], errors="coerce")
        df = df.sort_values(["priority_num"], ascending=True, na_position="last")
        df = df.drop(columns=["priority_num"])

    for _, row in df.iterrows():
        priority = safe_text(row.get("priority"))
        theme = safe_text(row.get("theme"))
        category = _category_label(row.get("category"))
        status = _status_label(row.get("status"))

        with st.container(border=True):
            st.markdown(f"### 優先{priority}｜{theme}")
            c1, c2, c3 = st.columns(3)
            c1.write(f"**カテゴリ**：{category}")
            c2.write(f"**頻度**：{safe_text(row.get('frequency'))}")
            c3.write(f"**状態**：{status}")

            st.write(f"**課題**：{safe_text(row.get('issue'))}")
            st.write(f"**行動**：{safe_text(row.get('action'))}")
            st.write(f"**関連メニュー**：{safe_text(row.get('related_training'))}")

            target = safe_text(row.get("target_period"))
            if target != "—":
                st.caption(f"対象期間：{target}")

            review_comment = safe_text(row.get("review_comment"))
            if review_comment != "—":
                st.info(review_comment)


def _render_review(st, df_review: pd.DataFrame) -> None:
    section_title(
        st,
        "⑤ IDPレビュー｜成長確認",
        "評価表ではなく、努力・変化・次の一手を確認する画面です。テキスト入力は任意です。",
    )

    if df_review is None or df_review.empty:
        st.info("IDP_Review にデータがありません。")
        return

    df = df_review.copy()

    if "priority" in df.columns:
        df["priority_num"] = pd.to_numeric(df["priority"], errors="coerce")
        df = df.sort_values(["review_month", "priority_num"], ascending=[False, True], na_position="last")
        df = df.drop(columns=["priority_num"])

    for _, row in df.iterrows():
        month = safe_text(row.get("review_month"))
        priority = safe_text(row.get("priority"))
        theme = safe_text(row.get("theme"))
        category = _category_label(row.get("category"))

        with st.container(border=True):
            st.markdown(f"### {month}｜優先{priority}｜{theme}")
            st.caption(f"カテゴリ：{category}")

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("実行", score_badge(row.get("execution_score")))
            c2.metric("意識", score_badge(row.get("awareness_score")))
            c3.metric("変化", score_badge(row.get("change_score")))
            c4.metric("総合", score_badge(row.get("overall_score")))

            d1, d2 = st.columns(2)
            d1.write(f"**来月判断**：{safe_text(row.get('continue_decision'))}")
            d2.write(f"**次の優先度**：{safe_text(row.get('next_priority'))}")

            good = safe_text(row.get("good_point"))
            issue = safe_text(row.get("issue"))
            next_action = safe_text(row.get("next_action"))
            evidence = safe_text(row.get("evidence_text"))
            parent_comment = safe_text(row.get("parent_comment"))
            pep_comment = safe_text(row.get("pep_comment"))

            optional_lines = []
            if good != "—":
                optional_lines.append(f"**できたこと**：{good}")
            if issue != "—":
                optional_lines.append(f"**課題**：{issue}")
            if next_action != "—":
                optional_lines.append(f"**次にやること**：{next_action}")
            if evidence != "—":
                optional_lines.append(f"**根拠メモ**：{evidence}")
            if parent_comment != "—":
                optional_lines.append(f"**保護者メモ**：{parent_comment}")
            if pep_comment != "—":
                optional_lines.append(f"**Pepコメント**：{pep_comment}")

            if optional_lines:
                for line in optional_lines:
                    st.write(line)
            else:
                st.caption("テキストメモは未入力です。選択式評価だけでもOKです。")


def render_idp(st, storage) -> None:
    st.header("IDP｜個別育成プラン")

    st.info(
        "IDPは、目標・強み・課題・行動・振り返りをまとめて確認するページです。"
        "まずはSheetsの内容を読み込んで表示します。編集機能は次フェーズで追加します。"
    )

    if not hasattr(storage, "supports_idp") or not storage.supports_idp():
        st.error("現在のstorageではIDP機能が利用できません。")
        return

    ok, msg = storage.idp_healthcheck()
    if ok:
        st.success(msg)
    else:
        st.warning(msg)

    try:
        df_profile = storage.load_all_idp_profile()
        df_goals = storage.load_all_idp_goals()
        df_player = storage.load_all_idp_player_profile()
        df_action = storage.load_all_idp_action_plan()
        df_review = storage.load_all_idp_review()
    except Exception as e:
        st.error(f"IDPデータの読み込みに失敗しました：{e}")
        return

    _render_profile(st, df_profile)
    st.divider()

    _render_goals(st, df_goals)
    st.divider()

    _render_player_profile(st, df_player)
    st.divider()

    _render_action_plan(st, df_action)
    st.divider()

    _render_review(st, df_review)