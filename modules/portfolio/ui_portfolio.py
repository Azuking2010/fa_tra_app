# ui_portfolio.py
from __future__ import annotations

from datetime import date
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from portfolio_storage import PortfolioStorage, PORTFOLIO_COLUMNS


# =========================
# helpers
# =========================
def _bmi(height_cm: float, weight_kg: float) -> Optional[float]:
    if height_cm <= 0 or weight_kg <= 0:
        return None
    m = height_cm / 100.0
    return round(weight_kg / (m * m), 2)


def _is_blank(v: Any) -> bool:
    if v is None:
        return True
    s = str(v).strip()
    return s == "" or s.lower() in ["nan", "none"]


def _to_float_or_none(v: Any) -> Optional[float]:
    if _is_blank(v):
        return None
    try:
        fv = float(v)
        if pd.isna(fv):
            return None
        return fv
    except Exception:
        return None


def _valid_numeric(v: Any) -> Optional[float]:
    """
    数値の有効判定：
    - None/NaN/空は無効
    - 0 は無効（＝空扱い）
    """
    fv = _to_float_or_none(v)
    if fv is None:
        return None
    if fv == 0.0:
        return None
    return fv


def _valid_text(v: Any) -> Optional[str]:
    if _is_blank(v):
        return None
    s = str(v).strip()
    if s == "" or s.lower() == "nan":
        return None
    return s


def _valid_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    if isinstance(v, bool):
        return v
    s = str(v).strip().lower()
    if s in ["true", "1", "yes", "y", "on"]:
        return True
    if s in ["false", "0", "no", "n", "off"]:
        return False
    return None


def _num_default(source: Dict[str, Any], key: str, fallback: float = 0.0) -> float:
    v = _valid_numeric(source.get(key, None))
    return float(v) if v is not None else fallback


def _text_default(source: Dict[str, Any], key: str, fallback: str = "") -> str:
    v = _valid_text(source.get(key, None))
    return str(v) if v is not None else fallback


def _prev_caption(latest_all: Dict[str, Any], key: str) -> None:
    """
    前回値表示（latest_allは「全期間」の最新値辞書）
    数値は 0 を表示しない。nan/空も表示しない。
    """
    v = latest_all.get(key, None)

    # bool は True/False を表示してよい（tcenter用）
    vb = _valid_bool(v)
    if vb is not None and key == "tcenter":
        st.caption(f"前回値：{vb}")
        return

    fv = _valid_numeric(v)
    if fv is not None:
        st.caption(f"前回値：{fv}")
        return

    tv = _valid_text(v)
    if tv is not None:
        st.caption(f"前回値：{tv}")
        return


def _try_get_all_df(storage: PortfolioStorage) -> pd.DataFrame:
    """
    PortfolioStorageの実装差異に備えて、全件DF取得をなるべく頑丈にする。
    優先順：
      1) storage.load_all_df()
      2) storage.load_all() / storage.load_all_records()
      3) storage.get_all_df()
      4) 最後に空DF
    """
    for fn in ["load_all_df", "load_all", "load_all_records", "get_all_df"]:
        if hasattr(storage, fn):
            try:
                df = getattr(storage, fn)()
                if isinstance(df, pd.DataFrame):
                    return df
            except Exception:
                pass
    return pd.DataFrame(columns=PORTFOLIO_COLUMNS)


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

    # 欠け列補完
    for c in PORTFOLIO_COLUMNS:
        if c not in df.columns:
            df[c] = ""

    # date を datetime に寄せる（失敗してもOK）
    if "date" in df.columns:
        df["_date_dt"] = pd.to_datetime(df["date"], errors="coerce")
    else:
        df["_date_dt"] = pd.NaT

    return df


def _latest_values_from_df(df: pd.DataFrame) -> Dict[str, Any]:
    """
    全期間から「非空欄の最新値」を列ごとに拾う。
    日付でソート（_date_dt -> date文字列）してから最後に近い有効値を採用。
    """
    if df is None or df.empty:
        return {}

    dfx = df.copy()

    # 日付が取れる行を優先して昇順ソート（取れない行は最後に回る可能性があるが許容）
    if "_date_dt" in dfx.columns:
        dfx = dfx.sort_values(by=["_date_dt", "date"], ascending=True, na_position="last")
    else:
        dfx = dfx.sort_values(by=["date"], ascending=True)

    latest: Dict[str, Any] = {}

    # 末尾から走査して最初に見つかった有効値を採用
    for col in PORTFOLIO_COLUMNS:
        if col not in dfx.columns:
            continue
        series = dfx[col].tolist()

        chosen: Any = None

        if col == "tcenter":
            # bool は 0/空でも「False」として保存されていることがあるので、
            # ここは「空でない最新」を採用（True/FalseどちらでもOK）
            for v in reversed(series):
                if _is_blank(v):
                    continue
                vb = _valid_bool(v)
                if vb is not None:
                    chosen = vb
                    break
            if chosen is not None:
                latest[col] = chosen
            continue

        # 数値系（0は無効）
        if col in [
            "height_cm",
            "weight_kg",
            "bmi",
            "run_100m_sec",
            "run_1500m_sec",
            "run_3000m_sec",
            "rank",
            "deviation",
            "score_jp",
            "score_math",
            "score_en",
            "score_sci",
            "score_soc",
            "rating",
        ]:
            for v in reversed(series):
                fv = _valid_numeric(v)
                if fv is None:
                    continue
                chosen = fv
                break
            if chosen is not None:
                latest[col] = chosen
            continue

        # テキスト系（空は無効）
        for v in reversed(series):
            tv = _valid_text(v)
            if tv is None:
                continue
            chosen = tv
            break
        if chosen is not None:
            latest[col] = chosen

    return latest


def _values_for_selected_date(df: pd.DataFrame, d: date) -> Dict[str, Any]:
    """
    選択日付の行があるなら、その行の値を返す。
    ただし、数値0/空/nanは無効扱い＝返さない（入力欄は空になる）。
    同一日付が複数ある場合は「最後の行」を優先。
    """
    if df is None or df.empty or "date" not in df.columns:
        return {}

    key = d.isoformat()
    dfx = df.copy()
    dfx["date"] = dfx["date"].astype(str)

    hit = dfx[dfx["date"] == key]
    if hit.empty:
        return {}

    row = hit.iloc[-1].to_dict()

    out: Dict[str, Any] = {}

    # 数値：>0だけ
    numeric_cols = [
        "height_cm",
        "weight_kg",
        "bmi",
        "run_100m_sec",
        "run_1500m_sec",
        "run_3000m_sec",
        "rank",
        "deviation",
        "score_jp",
        "score_math",
        "score_en",
        "score_sci",
        "score_soc",
        "rating",
    ]
    for c in numeric_cols:
        v = _valid_numeric(row.get(c, None))
        if v is not None:
            out[c] = v

    # テキスト
    text_cols = [
        "track_meet",
        "soccer_tournament",
        "match_result",
        "video_url",
        "video_note",
        "note",
    ]
    for c in text_cols:
        v = _valid_text(row.get(c, None))
        if v is not None:
            out[c] = v

    # bool（空でなければ採用）
    vb = _valid_bool(row.get("tcenter", None))
    if vb is not None:
        out["tcenter"] = vb

    return out


# =========================
# main UI
# =========================
def render_portfolio_page(portfolio_storage: PortfolioStorage) -> None:
    st.title("ポートフォリオ（実績/成長記録）")

    # ヘッダチェック
    portfolio_storage.ensure_header()

    # 全件DF（可能なら）
    df_all = _normalize_df(_try_get_all_df(portfolio_storage))

    # 前回値（＝全期間の最新値）…選択日付に関係なく表示するため必ずここで作る
    latest_all: Dict[str, Any] = {}
    try:
        # 既存の実装があるならそれを優先（ただし日付に依存しないことが前提）
        if hasattr(portfolio_storage, "get_latest_values"):
            latest_all = portfolio_storage.get_latest_values() or {}
        # get_latest_values が「選択日付依存」になってしまっている可能性に備え、
        # DFから作った値で上書きできるようにする
        latest_from_df = _latest_values_from_df(df_all)
        # DF由来が取れるなら優先（より確実に「全期間」になる）
        if latest_from_df:
            latest_all = latest_from_df
    except Exception:
        latest_all = _latest_values_from_df(df_all)

    st.success("portfolio シートに接続OK")

    # ① 基本
    st.subheader("① 基本")
    d = st.date_input("日付", value=date.today())

    # 選択日付の行があれば、それを入力欄に反映（無ければ空）
    selected_values = _values_for_selected_date(df_all, d)

    if not selected_values:
        st.info("この日付の記録はまだありません（入力欄は空＝0扱い）")
    else:
        st.success("この日付の記録を読み込みました（入力欄に反映）")

    # ② 体
    st.subheader("② 体（body）")
    c1, c2 = st.columns(2)
    with c1:
        height_cm = st.number_input(
            "身長 (cm)",
            min_value=0.0,
            step=0.5,
            value=_num_default(selected_values, "height_cm", 0.0),
            format="%.2f",
        )
        _prev_caption(latest_all, "height_cm")

    with c2:
        weight_kg = st.number_input(
            "体重 (kg)",
            min_value=0.0,
            step=0.1,
            value=_num_default(selected_values, "weight_kg", 0.0),
            format="%.2f",
        )
        _prev_caption(latest_all, "weight_kg")

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
            value=_num_default(selected_values, "run_100m_sec", 0.0),
            format="%.2f",
        )
        _prev_caption(latest_all, "run_100m_sec")
    with t2:
        run_1500 = st.number_input(
            "1500m (sec)",
            min_value=0.0,
            step=1.0,
            value=_num_default(selected_values, "run_1500m_sec", 0.0),
            format="%.2f",
        )
        _prev_caption(latest_all, "run_1500m_sec")
    with t3:
        run_3000 = st.number_input(
            "3000m (sec)",
            min_value=0.0,
            step=1.0,
            value=_num_default(selected_values, "run_3000m_sec", 0.0),
            format="%.2f",
        )
        _prev_caption(latest_all, "run_3000m_sec")

    track_meet = st.text_input("陸上大会名（任意）", value=_text_default(selected_values, "track_meet", ""))
    # track_meet も前回値を出したいなら（任意）
    # _prev_caption(latest_all, "track_meet")

    # ④ 学業
    st.subheader("④ 学業（school）")
    s1, s2, s3 = st.columns(3)
    with s1:
        rank = st.number_input(
            "順位 (rank)",
            min_value=0.0,
            step=1.0,
            value=_num_default(selected_values, "rank", 0.0),
            format="%.2f",
        )
        _prev_caption(latest_all, "rank")
    with s2:
        deviation = st.number_input(
            "偏差値 (deviation)",
            min_value=0.0,
            step=0.1,
            value=_num_default(selected_values, "deviation", 0.0),
            format="%.2f",
        )
        _prev_caption(latest_all, "deviation")
    with s3:
        rating = st.number_input(
            "評点 (rating)",
            min_value=0.0,
            step=1.0,
            value=_num_default(selected_values, "rating", 0.0),
            format="%.2f",
        )
        _prev_caption(latest_all, "rating")

    g1, g2, g3, g4, g5 = st.columns(5)
    with g1:
        score_jp = st.number_input("国語", min_value=0.0, step=1.0, value=_num_default(selected_values, "score_jp", 0.0), format="%.2f")
        _prev_caption(latest_all, "score_jp")
    with g2:
        score_math = st.number_input("数学", min_value=0.0, step=1.0, value=_num_default(selected_values, "score_math", 0.0), format="%.2f")
        _prev_caption(latest_all, "score_math")
    with g3:
        score_en = st.number_input("英語", min_value=0.0, step=1.0, value=_num_default(selected_values, "score_en", 0.0), format="%.2f")
        _prev_caption(latest_all, "score_en")
    with g4:
        score_sci = st.number_input("理科", min_value=0.0, step=1.0, value=_num_default(selected_values, "score_sci", 0.0), format="%.2f")
        _prev_caption(latest_all, "score_sci")
    with g5:
        score_soc = st.number_input("社会", min_value=0.0, step=1.0, value=_num_default(selected_values, "score_soc", 0.0), format="%.2f")
        _prev_caption(latest_all, "score_soc")

    # ⑤ サッカー
    st.subheader("⑤ サッカー（soccer）")
    # 選択日付に値があればそれ、なければ False
    tcenter_default = selected_values.get("tcenter", False)
    tcenter = st.checkbox("トレセン (tcenter)", value=bool(tcenter_default))
    # 前回値表示（任意）
    _prev_caption(latest_all, "tcenter")

    soccer_tournament = st.text_input(
        "サッカー大会名（任意）",
        value=_text_default(selected_values, "soccer_tournament", ""),
    )

    match_result = st.text_area(
        "試合実績 (match_result)",
        value=_text_default(selected_values, "match_result", ""),
        height=80,
    )

    v1, v2 = st.columns(2)
    with v1:
        video_url = st.text_input("動画URL (video_url)", value=_text_default(selected_values, "video_url", ""))
    with v2:
        video_note = st.text_input("動画備考 (video_note)", value=_text_default(selected_values, "video_note", ""))

    # ⑥ 自由記述
    st.subheader("⑥ 自由記述（note）")
    note = st.text_area("メモ (note)", value=_text_default(selected_values, "note", ""), height=120)

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

        # append_row 内で「0→空白」変換する前提なのでここはそのまま
        portfolio_storage.append_row(row)

        st.success("保存しました（行追加）")
        st.rerun()
