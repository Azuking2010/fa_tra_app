# file: modules/ui_practice_log.py
# purpose: 練習後メモページのUIを担当する。日付ごとに練習・試合・自主練・勉強の自由記述メモを保存・表示する。

from __future__ import annotations

from datetime import date, datetime
from html import escape
from typing import Any

import pandas as pd


QUESTION_TRAINING = """チーム練習でやったこと、意識したこと、コーチから言われたこと、チーム全体に話されたことなど。
きれいに書かなくてOK。覚えていることをそのまま書く。"""

QUESTION_MATCH = """出場ポジション、試合で意識したこと、できたこと、できなかったこと、相手の特徴、コーチからの指摘など。
覚えていることだけでOK。"""

QUESTION_SELF_TRAINING = """チーム練習後や家でやったこと。
ドリブル、左足、ダッシュ、ストレッチ、体幹など。やった内容だけでもOK。"""

QUESTION_STUDY = """勉強した内容、テスト、提出物、英語、よかったこと、困ったことなど。
一言でもOK。"""


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


def _now_str() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _make_log_id(selected_date: date) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    return f"PL-{selected_date.strftime('%Y%m%d')}-{stamp}"


def _sort_logs(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    d = df.copy()

    if "date" in d.columns:
        d["_date_dt"] = pd.to_datetime(d["date"], errors="coerce")
    else:
        d["_date_dt"] = pd.NaT

    if "created_at" in d.columns:
        d["_created_dt"] = pd.to_datetime(d["created_at"], errors="coerce")
    else:
        d["_created_dt"] = pd.NaT

    d = d.sort_values(
        ["_date_dt", "_created_dt"],
        ascending=[False, False],
        na_position="last",
    )
    d = d.drop(columns=[c for c in ["_date_dt", "_created_dt"] if c in d.columns])
    return d.reset_index(drop=True)


def _render_question_box(st) -> None:
    with st.expander("何を書けばいい？", expanded=True):
        st.markdown(
            """
**きれいに書かなくてOK。**  
覚えていることを、そのまま短く残せばOKです。

- 今日、意識したこと
- チーム練習でやったこと
- 自主練でやったこと
- できたこと、良かったこと
- できなかったこと、悪かったこと
- コーチからの指摘
- チーム全体に話されたポイント
- 勉強でやったこと、困ったこと

帰宅途中に打てない日は、帰宅後にボイスメモでもOK。
"""
        )


def _has_any_text(*values: str) -> bool:
    return any(str(v).strip() for v in values)


def _render_recent_logs(st, df: pd.DataFrame) -> None:
    st.markdown("## 直近のメモ")

    if df is None or df.empty:
        st.info("まだ練習後メモはありません。")
        return

    d = _sort_logs(df).head(10)

    for _, row in d.iterrows():
        log_date = _html(row.get("date"), "—")
        created_at = _html(row.get("created_at"), "")
        training = _html(row.get("training_text"), "")
        match = _html(row.get("match_text"), "")
        self_training = _html(row.get("self_training_text"), "")
        study = _html(row.get("study_text"), "")

        with st.container(border=True):
            st.markdown(f"### {log_date}")
            if created_at:
                st.caption(f"保存：{created_at}")

            if training:
                st.markdown("**練習**")
                st.write(training)

            if match:
                st.markdown("**試合**")
                st.write(match)

            if self_training:
                st.markdown("**自主練**")
                st.write(self_training)

            if study:
                st.markdown("**勉強**")
                st.write(study)


def render_practice_log(st, storage) -> None:
    st.header("練習後メモ")

    st.markdown(
        """
これは評価用の日報ではありません。  
**忘れる前に、脳内に残っていることを残すためのメモ**です。

全部を埋めなくてOK。  
書けるところだけ書けばOKです。
"""
    )

    if not hasattr(storage, "supports_practice_log") or not storage.supports_practice_log():
        st.error("現在のstorageでは Practice_Log 機能が利用できません。")
        return

    ok, msg = storage.practice_log_healthcheck()
    if ok:
        st.success(msg)
    else:
        st.error(msg)
        st.info("Google Sheetsに Practice_Log シートを作り、指定ヘッダーを1行目に貼り付けてください。")
        return

    _render_question_box(st)

    selected_date = st.date_input("日付", value=date.today(), key="practice_log_date")

    st.divider()

    st.markdown("### 練習")
    st.caption(QUESTION_TRAINING)
    training_text = st.text_area(
        "練習メモ",
        value="",
        placeholder=QUESTION_TRAINING,
        height=150,
        key="practice_log_training_text",
        label_visibility="collapsed",
    )

    st.markdown("### 試合")
    st.caption(QUESTION_MATCH)
    match_text = st.text_area(
        "試合メモ",
        value="",
        placeholder=QUESTION_MATCH,
        height=150,
        key="practice_log_match_text",
        label_visibility="collapsed",
    )

    st.markdown("### 自主練")
    st.caption(QUESTION_SELF_TRAINING)
    self_training_text = st.text_area(
        "自主練メモ",
        value="",
        placeholder=QUESTION_SELF_TRAINING,
        height=150,
        key="practice_log_self_training_text",
        label_visibility="collapsed",
    )

    st.markdown("### 勉強")
    st.caption(QUESTION_STUDY)
    study_text = st.text_area(
        "勉強メモ",
        value="",
        placeholder=QUESTION_STUDY,
        height=150,
        key="practice_log_study_text",
        label_visibility="collapsed",
    )

    st.divider()

    if st.button("練習後メモを保存", type="primary", use_container_width=True):
        training_text = str(training_text).strip()
        match_text = str(match_text).strip()
        self_training_text = str(self_training_text).strip()
        study_text = str(study_text).strip()

        if not _has_any_text(training_text, match_text, self_training_text, study_text):
            st.warning("保存するメモがありません。どこか1つだけでも書いてください。")
            return

        now = _now_str()

        row = {
            "log_id": _make_log_id(selected_date),
            "date": str(selected_date),
            "training_text": training_text,
            "match_text": match_text,
            "self_training_text": self_training_text,
            "study_text": study_text,
            "source": "app",
            "created_at": now,
            "updated_at": now,
        }

        try:
            storage.append_practice_log_row(row)
            st.success("練習後メモを保存しました。")
            st.rerun()
        except Exception as e:
            st.error(f"保存に失敗しました：{e}")
            return

    st.divider()

    try:
        df_logs = storage.load_all_practice_log()
    except Exception as e:
        st.error(f"練習後メモの読み込みに失敗しました：{e}")
        return

    _render_recent_logs(st, df_logs)