# ui_portfolio.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

import streamlit as st

from portfolio_storage import PortfolioStorage, PORTFOLIO_COLUMNS


def _bmi(height_cm: float, weight_kg: float) -> Optional[float]:
    if height_cm <= 0 or weight_kg <= 0:
        return None
    m = height_cm / 100.0
    return round(weight_kg / (m * m), 2)


def _num_default(latest: Dict[str, Any], key: str, fallback: float = 0.0) -> float:
    v = latest.get(key, None)
    try:
        if v is None:
            return fallback
        # pandas float/str混在に強く
        fv = float(v)
        # 0は無効扱いなのでデフォルトに使わない（前回値としても表示しない方が自然）
        if fv == 0.0:
            return fallback
        return fv
    except Exception:
        return fallback


def _text_default(latest: Dict[str, Any], key: str, fallback: str = "") -> str:
    v = latest.get(key, None)
    if v is None:
        return fallback
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return fallback
    return s


def _prev_caption(latest: Dict[str, Any], key: str) -> None:
    """前回値表示（0は表示しない）"""
    v = latest.get(key, None)
    if v is None:
        return
    try:
        if isinstance(v, (int, float)) and float(v) == 0.0:
            return
    except Exception:
        pass
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return
    st.caption(f"前回値：{s}")


def render_portfolio_page(portfolio_storage: PortfolioStorage) -> None:
    st.title("ポートフォリオ（実績/成長記録）")

    # ヘッダチェック
    portfolio_storage.ensure_header()

    # 最新の“値”を取得（ここがポイント：最新行じゃなく、最新値）
    latest = portfolio_storage.get_latest_values()

    st.success("portfolio シートに接続OK")

    # ① 基本
    st.subheader("① 基本")
    d = st.date_input("日付", value=date.today())

    # ② 体
    st.subheader("② 体（body）")
    c1, c2 = st.columns(2)
    with c1:
        height_cm = st.number_input(
            "身長 (cm)",
            min_value=0.0,
            step=0.5,
            value=_num_default(latest, "height_cm", 0.0),
            format="%.2f",
        )
        _prev_caption(latest, "height_cm")

    with c2:
        weight_kg = st.number_input(
            "体重 (kg)",
            min_value=0.0,
            step=0.1,
            value=_num_default(latest, "weight_kg", 0.0),
            format="%.2f",
        )
        _prev_caption(latest, "weight_kg")

    bmi_val = _bmi(height_cm, weight_kg)
    if bmi_val is None:
        st.caption("BMI（参考）：—（保存はシート数式でもOK）")
    else:
        st.caption(f"BMI（参考）：{bmi_val}（保存はシート数式でもOK）")

    # ③ 陸上
    st.subheader("③ 陸上（track）")
    t1, t2, t3 = st.columns(3)
    with t1:
        run_100 = st.number_input(
            "100m (sec)",
            min_value=0.0,
            step=0.01,
            value=_num_default(latest, "run_100m_sec", 0.0),
            format="%.2f",
        )
        _prev_caption(latest, "run_100m_sec")
    with t2:
        run_1500 = st.number_input(
            "1500m (sec)",
            min_value=0.0,
            step=1.0,
            value=_num_default(latest, "run_1500m_sec", 0.0),
            format="%.2f",
        )
        _prev_caption(latest, "run_1500m_sec")
    with t3:
        run_3000 = st.number_input(
            "3000m (sec)",
            min_value=0.0,
            step=1.0,
            value=_num_default(latest, "run_3000m_sec", 0.0),
            format="%.2f",
        )
        _prev_caption(latest, "run_3000m_sec")

    track_meet = st.text_input("陸上大会名（任意）", value=_text_default(latest, "track_meet", ""))

    # ④ 学業
    st.subheader("④ 学業（school）")
    s1, s2, s3 = st.columns(3)
    with s1:
        rank = st.number_input(
            "順位 (rank)",
            min_value=0.0,
            step=1.0,
            value=_num_default(latest, "rank", 0.0),
            format="%.2f",
        )
        _prev_caption(latest, "rank")
    with s2:
        deviation = st.number_input(
            "偏差値 (deviation)",
            min_value=0.0,
            step=0.1,
            value=_num_default(latest, "deviation", 0.0),
            format="%.2f",
        )
        _prev_caption(latest, "deviation")
    with s3:
        rating = st.number_input(
            "評点 (rating)",
            min_value=0.0,
            step=1.0,
            value=_num_default(latest, "rating", 0.0),
            format="%.2f",
        )
        _prev_caption(latest, "rating")

    g1, g2, g3, g4, g5 = st.columns(5)
    with g1:
        score_jp = st.number_input("国語", min_value=0.0, step=1.0, value=_num_default(latest, "score_jp", 0.0), format="%.2f")
        _prev_caption(latest, "score_jp")
    with g2:
        score_math = st.number_input("数学", min_value=0.0, step=1.0, value=_num_default(latest, "score_math", 0.0), format="%.2f")
        _prev_caption(latest, "score_math")
    with g3:
        score_en = st.number_input("英語", min_value=0.0, step=1.0, value=_num_default(latest, "score_en", 0.0), format="%.2f")
        _prev_caption(latest, "score_en")
    with g4:
        score_sci = st.number_input("理科", min_value=0.0, step=1.0, value=_num_default(latest, "score_sci", 0.0), format="%.2f")
        _prev_caption(latest, "score_sci")
    with g5:
        score_soc = st.number_input("社会", min_value=0.0, step=1.0, value=_num_default(latest, "score_soc", 0.0), format="%.2f")
        _prev_caption(latest, "score_soc")

    # ⑤ サッカー
    st.subheader("⑤ サッカー（soccer）")
    tcenter_default = latest.get("tcenter", None)
    if tcenter_default is None:
        tcenter_default = False
    tcenter = st.checkbox("トレセン (tcenter)", value=bool(tcenter_default))

    soccer_tournament = st.text_input(
        "サッカー大会名（任意）",
        value=_text_default(latest, "soccer_tournament", ""),
    )

    match_result = st.text_area(
        "試合実績 (match_result)",
        value=_text_default(latest, "match_result", ""),
        height=80,
    )

    v1, v2 = st.columns(2)
    with v1:
        video_url = st.text_input("動画URL (video_url)", value=_text_default(latest, "video_url", ""))
    with v2:
        video_note = st.text_input("動画備考 (video_note)", value=_text_default(latest, "video_note", ""))

    # ⑥ 自由記述
    st.subheader("⑥ 自由記述（note）")
    note = st.text_area("メモ (note)", value=_text_default(latest, "note", ""), height=120)

    # 保存（行追加）
    if st.button("保存（行追加）", type="primary", use_container_width=True):
        row: Dict[str, Any] = {k: "" for k in PORTFOLIO_COLUMNS}

        row["date"] = d.isoformat()

        # body
        row["height_cm"] = float(height_cm)
        row["weight_kg"] = float(weight_kg)

        # bmi（保存は任意：Sheets数式でもOKだが、入れてもOK）
        if bmi_val is not None:
            row["bmi"] = float(bmi_val)

        # track
        row["run_100m_sec"] = float(run_100)
        row["run_1500m_sec"] = float(run_1500)
        row["run_3000m_sec"] = float(run_3000)
        row["track_meet"] = track_meet

        # school
        row["rank"] = float(rank)
        row["deviation"] = float(deviation)
        row["rating"] = float(rating)
        row["score_jp"] = float(score_jp)
        row["score_math"] = float(score_math)
        row["score_en"] = float(score_en)
        row["score_sci"] = float(score_sci)
        row["score_soc"] = float(score_soc)

        # soccer
        row["tcenter"] = bool(tcenter)
        row["soccer_tournament"] = soccer_tournament
        row["match_result"] = match_result
        row["video_url"] = video_url
        row["video_note"] = video_note

        # note
        row["note"] = note

        # append_row 内で「0→空白」変換するのでここはそのままでOK
        portfolio_storage.append_row(row)

        st.success("保存しました（行追加）")
        st.rerun()
