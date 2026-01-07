# modules/ui_portfolio.py
from __future__ import annotations

from datetime import date as date_type
from typing import Any, Dict, Optional

import streamlit as st

from modules.portfolio_utils import PORTFOLIO_COLUMNS, latest_non_empty_by_column, sanitize_float, sanitize_int


def _text_default(latest: Dict[str, str], key: str) -> str:
    v = latest.get(key, "")
    return "" if v is None else str(v)


def _num_default_float(latest: Dict[str, str], key: str) -> Optional[float]:
    return sanitize_float(latest.get(key))


def _num_default_int(latest: Dict[str, str], key: str) -> Optional[int]:
    return sanitize_int(latest.get(key))


def render_portfolio_page(
    st: Any,
    portfolio_storage,
    selected_date: date_type,
):
    ok, msg = portfolio_storage.healthcheck()
    if ok:
        st.success(msg)
    else:
        st.error(msg)
        return

    df = portfolio_storage.load_all()
    latest = latest_non_empty_by_column(df)

    st.subheader("＋ 新規追加（固定入力）")
    st.caption("空欄は保存しません（入力した項目だけが同じ日付で記録されます）。")

    # 日付（固定）
    st.write("### 日付")
    d = st.date_input("date", value=selected_date, key="pf_date")

    # -----------------------
    # ブロック1：身体
    # -----------------------
    st.write("### ① 身体（body）")
    col1, col2 = st.columns(2)

    with col1:
        use_height = st.checkbox("身長を入力", value=(_num_default_float(latest, "height_cm") is not None), key="pf_use_height")
        height_cm = st.text_input("身長 (cm)", value=str(_num_default_float(latest, "height_cm") or ""), key="pf_height")

    with col2:
        use_weight = st.checkbox("体重を入力", value=(_num_default_float(latest, "weight_kg") is not None), key="pf_use_weight")
        weight_kg = st.text_input("体重 (kg)", value=str(_num_default_float(latest, "weight_kg") or ""), key="pf_weight")

    st.info("BMI はシート側で自動計算します（身長/体重が空ならBMIも空）。")

    # -----------------------
    # ブロック2：陸上
    # -----------------------
    st.write("### ② 陸上（track）")
    c1, c2, c3 = st.columns(3)
    with c1:
        use_100 = st.checkbox("100m", value=(_num_default_float(latest, "run_100m_sec") is not None), key="pf_use_100")
        run_100 = st.text_input("100m (sec)", value=str(_num_default_float(latest, "run_100m_sec") or ""), key="pf_100")
    with c2:
        use_1500 = st.checkbox("1500m", value=(_num_default_float(latest, "run_1500m_sec") is not None), key="pf_use_1500")
        run_1500 = st.text_input("1500m (sec)", value=str(_num_default_float(latest, "run_1500m_sec") or ""), key="pf_1500")
    with c3:
        use_3000 = st.checkbox("3000m", value=(_num_default_float(latest, "run_3000m_sec") is not None), key="pf_use_3000")
        run_3000 = st.text_input("3000m (sec)", value=str(_num_default_float(latest, "run_3000m_sec") or ""), key="pf_3000")

    track_meet = st.text_input("陸上大会名（track_meet）", value=_text_default(latest, "track_meet"), key="pf_track_meet")

    # -----------------------
    # ブロック3：学力
    # -----------------------
    st.write("### ③ 学力（study）")
    c1, c2 = st.columns(2)
    with c1:
        use_rank = st.checkbox("順位(rank)", value=(_num_default_int(latest, "rank") is not None), key="pf_use_rank")
        rank = st.text_input("順位 (rank)", value=str(_num_default_int(latest, "rank") or ""), key="pf_rank")
    with c2:
        use_dev = st.checkbox("偏差値(deviation)", value=(_num_default_float(latest, "deviation") is not None), key="pf_use_dev")
        deviation = st.text_input("偏差値 (deviation)", value=str(_num_default_float(latest, "deviation") or ""), key="pf_dev")

    st.write("#### 各教科（score_*）")
    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        use_jp = st.checkbox("国語", value=(_num_default_float(latest, "score_jp") is not None), key="pf_use_jp")
        score_jp = st.text_input("国語", value=str(_num_default_float(latest, "score_jp") or ""), key="pf_jp")
    with s2:
        use_math = st.checkbox("数学", value=(_num_default_float(latest, "score_math") is not None), key="pf_use_math")
        score_math = st.text_input("数学", value=str(_num_default_float(latest, "score_math") or ""), key="pf_math")
    with s3:
        use_en = st.checkbox("英語", value=(_num_default_float(latest, "score_en") is not None), key="pf_use_en")
        score_en = st.text_input("英語", value=str(_num_default_float(latest, "score_en") or ""), key="pf_en")
    with s4:
        use_sci = st.checkbox("理科", value=(_num_default_float(latest, "score_sci") is not None), key="pf_use_sci")
        score_sci = st.text_input("理科", value=str(_num_default_float(latest, "score_sci") or ""), key="pf_sci")
    with s5:
        use_soc = st.checkbox("社会", value=(_num_default_float(latest, "score_soc") is not None), key="pf_use_soc")
        score_soc = st.text_input("社会", value=str(_num_default_float(latest, "score_soc") or ""), key="pf_soc")

    use_rating = st.checkbox("評点(rating)", value=(_num_default_float(latest, "rating") is not None), key="pf_use_rating")
    rating = st.text_input("評点 (rating)", value=str(_num_default_float(latest, "rating") or ""), key="pf_rating")

    # -----------------------
    # ブロック4：サッカー
    # -----------------------
    st.write("### ④ サッカー（soccer）")
    tcenter = st.checkbox("トレセン選出（tcenter）", value=(_text_default(latest, "tcenter").lower() in ["true", "1", "yes", "y", "selected", "on"]), key="pf_tcenter")
    soccer_tournament = st.text_input("サッカー大会名（soccer_tournament）", value=_text_default(latest, "soccer_tournament"), key="pf_soccer_tournament")
    match_result = st.text_area("試合実績（match_result）", value=_text_default(latest, "match_result"), height=90, key="pf_match")

    # -----------------------
    # ブロック5：動画
    # -----------------------
    st.write("### ⑤ 動画（video）")
    video_url = st.text_input("動画URL（video_url）", value=_text_default(latest, "video_url"), key="pf_video_url")
    video_note = st.text_area("動画備考（video_note）", value=_text_default(latest, "video_note"), height=70, key="pf_video_note")

    # -----------------------
    # ブロック6：メモ
    # -----------------------
    st.write("### ⑥ 自由記述（note）")
    note = st.text_area("メモ（note）", value=_text_default(latest, "note"), height=90, key="pf_note")

    # -----------------------
    # 保存処理（行追加）
    # -----------------------
    def _add_if(row: Dict[str, Any], key: str, val: Any):
        if val is None:
            return
        s = str(val).strip()
        if s != "":
            row[key] = s

    if st.button("保存（行追加）", type="primary"):
        row: Dict[str, Any] = {"date": d.strftime("%Y-%m-%d")}

        # 身体
        if use_height:
            _add_if(row, "height_cm", sanitize_float(height_cm))
        if use_weight:
            _add_if(row, "weight_kg", sanitize_float(weight_kg))

        # 陸上
        if use_100:
            _add_if(row, "run_100m_sec", sanitize_float(run_100))
        if use_1500:
            _add_if(row, "run_1500m_sec", sanitize_float(run_1500))
        if use_3000:
            _add_if(row, "run_3000m_sec", sanitize_float(run_3000))
        _add_if(row, "track_meet", track_meet)

        # 学力
        if use_rank:
            _add_if(row, "rank", sanitize_int(rank))
        if use_dev:
            _add_if(row, "deviation", sanitize_float(deviation))

        if use_jp:
            _add_if(row, "score_jp", sanitize_float(score_jp))
        if use_math:
            _add_if(row, "score_math", sanitize_float(score_math))
        if use_en:
            _add_if(row, "score_en", sanitize_float(score_en))
        if use_sci:
            _add_if(row, "score_sci", sanitize_float(score_sci))
        if use_soc:
            _add_if(row, "score_soc", sanitize_float(score_soc))

        if use_rating:
            _add_if(row, "rating", sanitize_float(rating))

        # サッカー
        row["tcenter"] = "true" if tcenter else ""
        _add_if(row, "soccer_tournament", soccer_tournament)
        _add_if(row, "match_result", match_result)

        # 動画・メモ
        _add_if(row, "video_url", video_url)
        _add_if(row, "video_note", video_note)
        _add_if(row, "note", note)

        # 1つも入ってない（date以外空）なら止める
        non_date_keys = [k for k in row.keys() if k != "date" and str(row.get(k, "")).strip() != ""]
        if not non_date_keys:
            st.warning("日付以外がすべて空です。入力してから保存してください。")
            return

        portfolio_storage.append_row(row)
        st.success("保存しました（行追加）")

    st.divider()
    st.write("### 直近の記録（参考）")
    try:
        if df is not None and not df.empty:
            st.dataframe(df.tail(20), use_container_width=True)
        else:
            st.caption("まだ記録がありません。")
    except Exception:
        st.caption("表示に失敗しました（データ量が多い場合は要調整）。")
