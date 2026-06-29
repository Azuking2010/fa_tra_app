# file: modules/ui_practice_log.py
# purpose: 練習/試合後メモページのUIを担当する。日付ごとに練習・試合・自主練・勉強の自由記述メモと、ストレッチ/ベルリッツの習慣チェックを保存・表示する。

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
ドリブル、左足、ダッシュ、体幹など。やった内容だけでもOK。
※ストレッチは上の習慣チェックで記録できます。"""

QUESTION_STUDY = """勉強した内容、テスト、提出物、英語、よかったこと、困ったことなど。
一言でもOK。
※月曜のベルリッツは上の習慣チェックで記録できます。"""


TEXT_INPUT_KEYS = [
    "practice_log_training_text",
    "practice_log_match_text",
    "practice_log_self_training_text",
    "practice_log_study_text",
]

CHECK_INPUT_KEYS = [
    "practice_log_stretch_done",
    "practice_log_berlitz_done",
]


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


def _is_monday(selected_date: date) -> bool:
    return selected_date.weekday() == 0


def _bool_to_sheet(value: bool) -> str:
    return "TRUE" if bool(value) else "FALSE"


def _as_bool(value: Any) -> bool | None:
    """
    Sheets/CSVから読み込んだ TRUE/FALSE/1/0/yes/no をboolへ寄せる。
    空欄は None として扱う。
    """
    if _is_blank(value):
        return None

    s = str(value).strip().lower()

    if s in ["true", "1", "yes", "y", "done", "済", "実施", "やった"]:
        return True

    if s in ["false", "0", "no", "n", "未", "未実施", "やってない"]:
        return False

    return None


def _status_badge(label: str, value: Any) -> str:
    b = _as_bool(value)

    if b is True:
        return f"✅ {label}：やった"

    if b is False:
        return f"⬜ {label}：やってない"

    return f"— {label}：未入力"


def _clear_input_boxes(st) -> None:
    """
    入力欄をクリアする。
    日付変更時・保存後に、前回入力内容が残り続けないようにする。
    """
    for key in TEXT_INPUT_KEYS:
        st.session_state[key] = ""

    for key in CHECK_INPUT_KEYS:
        st.session_state[key] = False


def _sync_selected_date_and_clear_if_needed(st, selected_date: date) -> None:
    """
    日付が変わったら入力欄をクリアする。
    これにより、別日付に移動した時に前日の未保存/保存済みメモが残らない。
    """
    current_date_text = str(selected_date)
    prev_date_text = st.session_state.get("practice_log_prev_selected_date")

    if prev_date_text is None:
        st.session_state["practice_log_prev_selected_date"] = current_date_text
        return

    if prev_date_text != current_date_text:
        _clear_input_boxes(st)
        st.session_state["practice_log_prev_selected_date"] = current_date_text


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


def _has_any_text(*values: str) -> bool:
    return any(str(v).strip() for v in values)


def _render_recent_logs(st, df: pd.DataFrame) -> None:
    st.markdown("## 直近のメモ")

    if df is None or df.empty:
        st.info("まだメモはありません。")
        return

    d = _sort_logs(df).head(10)

    for _, row in d.iterrows():
        log_date = _html(row.get("date"), "—")
        created_at = _txt(row.get("created_at"), "")

        training = _txt(row.get("training_text"), "")
        match = _txt(row.get("match_text"), "")
        self_training = _txt(row.get("self_training_text"), "")
        study = _txt(row.get("study_text"), "")

        stretch_status = _status_badge("ストレッチ", row.get("stretch_done"))
        berlitz_status = _status_badge("ベルリッツ", row.get("berlitz_done"))

        with st.container(border=True):
            st.markdown(f"### {log_date}")

            if created_at:
                st.caption(f"保存：{created_at}")

            st.caption(f"{stretch_status}　/　{berlitz_status}")

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
    st.header("📝 練習/試合後メモ")

    if not hasattr(storage, "supports_practice_log") or not storage.supports_practice_log():
        st.error("現在のstorageでは Practice_Log 機能が利用できません。")
        return

    ok, msg = storage.practice_log_healthcheck()
    if not ok:
        st.error(msg)
        st.info("Google Sheetsに Practice_Log シートを作り、指定ヘッダーを1行目に貼り付けてください。")
        return

    selected_date = st.date_input("日付", value=date.today(), key="practice_log_date")

    _sync_selected_date_and_clear_if_needed(st, selected_date)

    if st.session_state.pop("practice_log_clear_after_save", False):
        _clear_input_boxes(st)
        st.success("メモを保存しました。")

    st.divider()

    st.markdown("### ✅ 習慣チェック")
    st.caption("毎日のストレッチや、月曜のベルリッツなど、文章にしなくてもよい継続項目をチェックします。")

    stretch_done = st.checkbox(
        "ストレッチをやった",
        key="practice_log_stretch_done",
    )

    show_berlitz = _is_monday(selected_date)

    if show_berlitz:
        berlitz_done = st.checkbox(
            "ベルリッツ完了",
            key="practice_log_berlitz_done",
        )
    else:
        berlitz_done = False
        st.caption("ベルリッツのチェックは月曜日だけ表示します。")

    st.divider()

    st.markdown("### 練習")
    st.caption(QUESTION_TRAINING)
    training_text = st.text_area(
        "練習メモ",
        placeholder=QUESTION_TRAINING,
        height=150,
        key="practice_log_training_text",
        label_visibility="collapsed",
    )

    st.markdown("### 試合")
    st.caption(QUESTION_MATCH)
    match_text = st.text_area(
        "試合メモ",
        placeholder=QUESTION_MATCH,
        height=150,
        key="practice_log_match_text",
        label_visibility="collapsed",
    )

    st.markdown("### 自主練")
    st.caption(QUESTION_SELF_TRAINING)
    self_training_text = st.text_area(
        "自主練メモ",
        placeholder=QUESTION_SELF_TRAINING,
        height=150,
        key="practice_log_self_training_text",
        label_visibility="collapsed",
    )

    st.markdown("### 勉強")
    st.caption(QUESTION_STUDY)
    study_text = st.text_area(
        "勉強メモ",
        placeholder=QUESTION_STUDY,
        height=150,
        key="practice_log_study_text",
        label_visibility="collapsed",
    )

    st.divider()

    if st.button("メモを保存", type="primary", use_container_width=True):
        training_text = str(training_text).strip()
        match_text = str(match_text).strip()
        self_training_text = str(self_training_text).strip()
        study_text = str(study_text).strip()

        has_any_text = _has_any_text(training_text, match_text, self_training_text, study_text)
        has_any_check = bool(stretch_done) or bool(berlitz_done)

        if not has_any_text and not has_any_check:
            st.warning("保存する内容がありません。メモを書くか、習慣チェックを1つ以上入れてください。")
            return

        now = _now_str()

        row = {
            "log_id": _make_log_id(selected_date),
            "date": str(selected_date),
            "training_text": training_text,
            "match_text": match_text,
            "self_training_text": self_training_text,
            "study_text": study_text,
            "stretch_done": _bool_to_sheet(stretch_done),
            "berlitz_done": _bool_to_sheet(berlitz_done) if show_berlitz else "",
            "source": "app",
            "created_at": now,
            "updated_at": now,
        }

        try:
            storage.append_practice_log_row(row)
            st.session_state["practice_log_clear_after_save"] = True
            st.rerun()
        except Exception as e:
            st.error(f"保存に失敗しました：{e}")
            return

    st.divider()

    try:
        df_logs = storage.load_all_practice_log()
    except Exception as e:
        st.error(f"メモの読み込みに失敗しました：{e}")
        return

    _render_recent_logs(st, df_logs)