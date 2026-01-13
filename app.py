import streamlit as st
from datetime import date
import math

from modules.constants import (
    WEEKDAY_KEYS, WEEKDAY_JP, DAY_PLAN, DAY_TITLE, COMMON_RULES
)
from modules.menu_master import load_training_list
from modules.storage import build_storage
from modules.ui_daily import render_daily
from modules.ui_day_training import render_day_training
from modules.ui_weight import render_weight
from modules.ui_parent_view import render_parent_view

# ★月曜OFFで表示する用
from modules.box_breath_component import render_box_breath_ui


# ======================
# ページ設定
# ======================
st.set_page_config(page_title="FA期間 自主トレチェック", layout="centered")

# ======================
# CSS（文字サイズ調整）
# ======================
st.markdown(
    """
<style>
html, body, [class*="css"]  { font-size: 20px !important; }
h1 { font-size: 40px !important; }
h2 { font-size: 30px !important; }
h3 { font-size: 24px !important; }
label, p, li, div { font-size: 20px !important; }
a, button { font-size: 20px !important; }
</style>
""",
    unsafe_allow_html=True,
)


# ======================
# helper（空/0/NaN判定）
# ======================
def _is_nan(v) -> bool:
    try:
        return isinstance(v, float) and math.isnan(v)
    except Exception:
        return False


def _is_blank_like(v):
    """空/NaN/None/0 を『無効（=空扱い）』にする"""
    if v is None:
        return True
    if _is_nan(v):
        return True
    if isinstance(v, str):
        s = v.strip()
        return s == "" or s.lower() in ["nan", "none", "null"]
    if isinstance(v, (int, float)):
        try:
            fv = float(v)
            if _is_nan(fv):
                return True
            return fv == 0.0
        except Exception:
            return False
    return False


def _latest_non_empty(df, col):
    """
    dfの末尾から遡って、最初に見つかった「空でない値」を返す。
    ※ここでの「空でない」は 0 を除外（0は無効値扱い）
    """
    if df is None or df.empty or col not in df.columns:
        return None

    s = df[col]

    # object（文字列など）
    if s.dtype == object:
        vals = s.astype(str).tolist()
        for v in reversed(vals):
            vv = str(v).strip()
            if vv.lower() in ["nan", "none", "null"]:
                vv = ""
            # "0" も無効扱い
            if vv == "" or vv == "0" or vv == "0.0":
                continue
            return vv
        return None

    # 数値
    try:
        vals = s.tolist()
        for v in reversed(vals):
            if v is None:
                continue
            try:
                fv = float(v)
            except Exception:
                continue
            if _is_nan(fv):
                continue
            if fv == 0.0:
                continue
            return fv
        return None
    except Exception:
        return None


def _latest_bool(df, col):
    """同日の行の中で、最後に出てきた bool を採用（無ければFalse）"""
    if df is None or df.empty or col not in df.columns:
        return False
    # boolは0/1扱いになるケースもあるので、文字列判定に寄せる
    vals = df[col].tolist()
    for v in reversed(vals):
        if v is None:
            continue
        s = str(v).strip().lower()
        if s in ["true", "1", "yes", "y", "on"]:
            return True
        if s in ["false", "0", "no", "n", "off"]:
            return False
    return False


def _prev_caption(st_container, v):
    """前回値：表示（0/空/NaNは表示しない）"""
    if _is_blank_like(v):
        return
    st_container.caption(f"前回値：{v}")


def _num_default(v, fallback=0.0):
    """number_input用：未入力（空扱い）の場合は 0 を入れる"""
    if _is_blank_like(v):
        return float(fallback)
    try:
        fv = float(v)
        if _is_nan(fv):
            return float(fallback)
        return fv
    except Exception:
        return float(fallback)


def _text_default(v, fallback=""):
    """text_input/text_area用：未入力（空扱い）の場合は空文字"""
    if v is None:
        return fallback
    s = str(v).strip()
    if s == "" or s.lower() in ["nan", "none", "null"]:
        return fallback
    return s


def _sec_to_min_sec(total_seconds):
    """秒→(分,秒) / None,0,NaNは(0,0)"""
    if total_seconds is None:
        return 0, 0
    try:
        fv = float(total_seconds)
        if _is_nan(fv) or fv <= 0:
            return 0, 0
        sec_int = int(round(fv))
        m = sec_int // 60
        s = sec_int % 60
        return m, s
    except Exception:
        return 0, 0


def _mmss_str(total_seconds):
    """秒→ 'm:ss'（無効なら '—'）"""
    m, s = _sec_to_min_sec(total_seconds)
    if m == 0 and s == 0:
        return "—"
    return f"{m}:{s:02d}"


def _prev_time_caption(st_container, sec_value):
    """前回値：m:ss（xxx sec）"""
    if _is_blank_like(sec_value):
        return
    try:
        fv = float(sec_value)
        if _is_nan(fv) or fv <= 0:
            return
        mmss = _mmss_str(fv)
        st_container.caption(f"前回値：{mmss}（{int(round(fv))} sec）")
    except Exception:
        return


def _filter_portfolio_by_date(dfp, selected_date: date):
    """
    portfolio全件dfから、selected_date の行だけ抽出。
    date列が 'YYYY-MM-DD' 以外でも、parseできるものは date として比較する。
    """
    if dfp is None or dfp.empty:
        return dfp

    if "date" not in dfp.columns:
        return dfp.iloc[0:0].copy()

    try:
        dcol = dfp["date"]
        dt = None
        # まずdatetime変換（失敗はNaT）
        dt = __import__("pandas").to_datetime(dcol, errors="coerce")
        mask = dt.dt.date == selected_date
        out = dfp.loc[mask].copy()
        return out
    except Exception:
        # フォールバック：文字列一致
        iso = str(selected_date)
        mask = dfp["date"].astype(str).str.strip() == iso
        return dfp.loc[mask].copy()


# ======================
# portfolio UI（固定入力 / 日付連動）
#  - checkbox廃止
#  - 0は保存しない（空白扱い）
#  - 前回値表示は「同日内の最新値」
#  - 1500/3000は「分＋秒」入力 → 保存時に秒へ変換
# ======================
def render_portfolio_fixed(st, storage):
    st.subheader("ポートフォリオ（実績/成長記録）")

    if not storage.supports_portfolio():
        st.error("Sheets接続ではないため portfolio は無効（CSV fallback）")
        st.info("※いまは安全のため、portfolio は Sheets 接続時のみ有効にしています。")
        return

    ok, msg = storage.portfolio_healthcheck()
    if ok:
        st.success(msg)
    else:
        st.error(msg)
        return

    # 全件を読む（この後、selected_date で絞る）
    dfp_all = storage.load_all_portfolio()

    # ① 基本（まず日付を選ばせる）
    st.markdown("### ① 基本")
    selected_date = st.date_input("日付", value=date.today(), key="pf_date")

    # 選択日のみ抽出
    dfp = _filter_portfolio_by_date(dfp_all, selected_date)

    if dfp is None or dfp.empty:
        st.info("この日付の記録はまだありません（入力欄は空＝0扱い）")
    else:
        st.success("この日付の記録を読み込みました（同日の最新値を入力欄に反映）")

    # ----------------------
    # ② 体（身長/体重）
    # ----------------------
    st.markdown("### ② 体（body）")
    c1, c2 = st.columns(2)

    day_height = _latest_non_empty(dfp, "height_cm")
    day_weight = _latest_non_empty(dfp, "weight_kg")

    height_cm = c1.number_input(
        "身長 (cm)",
        min_value=0.0,
        max_value=250.0,
        value=_num_default(day_height, 0.0),
        step=0.1,
        key="pf_height_cm",
    )
    _prev_caption(c1, day_height)

    weight_kg = c2.number_input(
        "体重 (kg)",
        min_value=0.0,
        max_value=200.0,
        value=_num_default(day_weight, 0.0),
        step=0.1,
        key="pf_weight_kg",
    )
    _prev_caption(c2, day_weight)

    bmi_preview = None
    if height_cm > 0 and weight_kg > 0:
        bmi_preview = weight_kg / ((height_cm / 100.0) ** 2)
        st.caption(f"BMI（参考）: {bmi_preview:.2f}  ※保存はシート数式でもOK")
    else:
        st.caption("BMI（参考）: —  ※保存はシート数式でもOK")

    # ----------------------
    # ③ 陸上（タイム）
    # ----------------------
    st.markdown("### ③ 陸上（track）")
    day_50 = _latest_non_empty(dfp, "run_100m_sec")  # 列名は互換維持（UIは50m）
    day_1500 = _latest_non_empty(dfp, "run_1500m_sec")
    day_3000 = _latest_non_empty(dfp, "run_3000m_sec")
    day_meet = _latest_non_empty(dfp, "track_meet")

    cc1, cc2, cc3 = st.columns(3)

    run_50 = cc1.number_input(
        "50m (sec)",
        min_value=0.0,
        max_value=9999.0,
        value=_num_default(day_50, 0.0),
        step=0.01,
        key="pf_run_100",  # 既存key維持
    )
    _prev_caption(cc1, day_50)

    d1500_m, d1500_s = _sec_to_min_sec(day_1500)
    d3000_m, d3000_s = _sec_to_min_sec(day_3000)

    cc2.markdown("**1500m (min:sec)**")
    m1500, s1500 = cc2.columns([1, 1])
    run_1500_min = m1500.number_input(
        "分",
        min_value=0,
        max_value=999,
        value=int(d1500_m),
        step=1,
        key="pf_run_1500_min",
    )
    run_1500_sec = s1500.number_input(
        "秒",
        min_value=0,
        max_value=59,
        value=int(d1500_s),
        step=1,
        key="pf_run_1500_sec",
    )
    _prev_time_caption(cc2, day_1500)

    cc3.markdown("**3000m (min:sec)**")
    m3000, s3000 = cc3.columns([1, 1])
    run_3000_min = m3000.number_input(
        "分 ",
        min_value=0,
        max_value=999,
        value=int(d3000_m),
        step=1,
        key="pf_run_3000_min",
    )
    run_3000_sec = s3000.number_input(
        "秒 ",
        min_value=0,
        max_value=59,
        value=int(d3000_s),
        step=1,
        key="pf_run_3000_sec",
    )
    _prev_time_caption(cc3, day_3000)

    run_1500_total = int(run_1500_min) * 60 + int(run_1500_sec)
    run_3000_total = int(run_3000_min) * 60 + int(run_3000_sec)

    cc2.caption(f"入力値：{run_1500_min}:{int(run_1500_sec):02d}（{run_1500_total} sec）" if run_1500_total > 0 else "入力値：—")
    cc3.caption(f"入力値：{run_3000_min}:{int(run_3000_sec):02d}（{run_3000_total} sec）" if run_3000_total > 0 else "入力値：—")

    track_meet = st.text_input(
        "陸上大会名（任意）",
        value=_text_default(day_meet, ""),
        key="pf_track_meet",
    )

    # ----------------------
    # ④ 学業（テスト）
    # ----------------------
    st.markdown("### ④ 学業（school）")
    day_rank = _latest_non_empty(dfp, "rank")
    day_dev = _latest_non_empty(dfp, "deviation")
    day_jp = _latest_non_empty(dfp, "score_jp")
    day_math = _latest_non_empty(dfp, "score_math")
    day_en = _latest_non_empty(dfp, "score_en")
    day_sci = _latest_non_empty(dfp, "score_sci")
    day_soc = _latest_non_empty(dfp, "score_soc")
    day_rating = _latest_non_empty(dfp, "rating")

    s1, s2, s3 = st.columns(3)
    rank = s1.number_input("順位 (rank)", min_value=0.0, max_value=99999.0, value=_num_default(day_rank, 0.0), step=1.0, key="pf_rank")
    _prev_caption(s1, day_rank)

    deviation = s2.number_input("偏差値 (deviation)", min_value=0.0, max_value=100.0, value=_num_default(day_dev, 0.0), step=0.1, key="pf_deviation")
    _prev_caption(s2, day_dev)

    rating = s3.number_input("評点 (rating)", min_value=0.0, max_value=999.0, value=_num_default(day_rating, 0.0), step=0.1, key="pf_rating")
    _prev_caption(s3, day_rating)

    t1, t2, t3, t4, t5 = st.columns(5)
    score_jp = t1.number_input("国語", min_value=0.0, max_value=200.0, value=_num_default(day_jp, 0.0), step=1.0, key="pf_score_jp")
    _prev_caption(t1, day_jp)

    score_math = t2.number_input("数学", min_value=0.0, max_value=200.0, value=_num_default(day_math, 0.0), step=1.0, key="pf_score_math")
    _prev_caption(t2, day_math)

    score_en = t3.number_input("英語", min_value=0.0, max_value=200.0, value=_num_default(day_en, 0.0), step=1.0, key="pf_score_en")
    _prev_caption(t3, day_en)

    score_sci = t4.number_input("理科", min_value=0.0, max_value=200.0, value=_num_default(day_sci, 0.0), step=1.0, key="pf_score_sci")
    _prev_caption(t4, day_sci)

    score_soc = t5.number_input("社会", min_value=0.0, max_value=200.0, value=_num_default(day_soc, 0.0), step=1.0, key="pf_score_soc")
    _prev_caption(t5, day_soc)

    # ----------------------
    # ⑤ サッカー（実績）
    # ----------------------
    st.markdown("### ⑤ サッカー（soccer）")
    day_tcenter = _latest_bool(dfp, "tcenter")
    day_soc_tour = _latest_non_empty(dfp, "soccer_tournament")
    day_match = _latest_non_empty(dfp, "match_result")
    day_url = _latest_non_empty(dfp, "video_url")
    day_vnote = _latest_non_empty(dfp, "video_note")

    tcenter = st.checkbox("トレセン（tcenter）", value=bool(day_tcenter), key="pf_tcenter")

    soccer_tournament = st.text_input("サッカー大会名（任意）", value=_text_default(day_soc_tour, ""), key="pf_soccer_tournament")
    match_result = st.text_input("試合実績（match_result）", value=_text_default(day_match, ""), key="pf_match_result")

    v1, v2 = st.columns(2)
    video_url = v1.text_input("動画URL（video_url）", value=_text_default(day_url, ""), key="pf_video_url")
    video_note = v2.text_input("動画備考（video_note）", value=_text_default(day_vnote, ""), key="pf_video_note")

    # ----------------------
    # ⑥ 自由記述
    # ----------------------
    st.markdown("### ⑥ 自由記述（note）")
    day_note = _latest_non_empty(dfp, "note")
    note = st.text_area("メモ（note）", value=_text_default(day_note, ""), height=120, key="pf_note")

    st.divider()

    # ======================
    # 保存（行追加）
    #  - 数値は0なら保存しない（空白扱い）
    #  - 文字列は空なら保存しない
    #  - tcenterは履歴として残すため常に保存（False/True）
    #  - bmiは基本保存しない（Sheets数式運用）
    # ======================
    if st.button("保存（行追加）", type="primary", use_container_width=True):
        row = {"date": str(selected_date)}

        if height_cm != 0:
            row["height_cm"] = float(height_cm)
        if weight_kg != 0:
            row["weight_kg"] = float(weight_kg)

        # bmi：保存しない（Sheets側の式でOK）

        # 50m（列名は互換維持：run_100m_sec）
        if run_50 != 0:
            row["run_100m_sec"] = float(run_50)

        if run_1500_total != 0:
            row["run_1500m_sec"] = float(run_1500_total)
        if run_3000_total != 0:
            row["run_3000m_sec"] = float(run_3000_total)

        if str(track_meet).strip():
            row["track_meet"] = str(track_meet).strip()

        if rank != 0:
            row["rank"] = float(rank)
        if deviation != 0:
            row["deviation"] = float(deviation)
        if rating != 0:
            row["rating"] = float(rating)

        if score_jp != 0:
            row["score_jp"] = float(score_jp)
        if score_math != 0:
            row["score_math"] = float(score_math)
        if score_en != 0:
            row["score_en"] = float(score_en)
        if score_sci != 0:
            row["score_sci"] = float(score_sci)
        if score_soc != 0:
            row["score_soc"] = float(score_soc)

        # tcenterは常に保存
        row["tcenter"] = bool(tcenter)

        if str(soccer_tournament).strip():
            row["soccer_tournament"] = str(soccer_tournament).strip()
        if str(match_result).strip():
            row["match_result"] = str(match_result).strip()
        if str(video_url).strip():
            row["video_url"] = str(video_url).strip()
        if str(video_note).strip():
            row["video_note"] = str(video_note).strip()
        if str(note).strip():
            row["note"] = str(note).strip()

        meaningful = [k for k in row.keys() if k not in ["date"]]
        if len(meaningful) == 0:
            st.warning("保存する値がありません（全て空欄）")
        else:
            storage.append_portfolio_row(row)
            st.success("保存しました（行追加）")
            st.caption("※この日付の最新値は『日付フィルタ後の最新値』として扱われます")


# ======================
# Storage / Master
# ======================
storage = build_storage(st)  # secrets があれば Sheets、なければ CSV
train_df = load_training_list()

# ======================
# UI
# ======================
st.title("FA期間 自主トレチェック")

# サイドバー：接続状態など
with st.sidebar:
    st.header("設定 / 状態")
    ok, msg = storage.healthcheck()
    if ok:
        st.success(msg)
    else:
        st.error(msg)

    info = storage.get_info()
    if info:
        if "spreadsheet_id" in info:
            st.caption(f"spreadsheet_id:\n{info['spreadsheet_id']}")
        if "worksheet" in info:
            st.caption(f"worksheet: {info['worksheet']}")
        if "portfolio_worksheet" in info:
            st.caption(f"portfolio_worksheet: {info['portfolio_worksheet']}")

    st.divider()
    st.caption("ページ")
    page = st.radio("ページ", ["トレーニング", "ポートフォリオ"], index=0, label_visibility="collapsed")

# ======================
# ページ切替
# ======================
if page == "ポートフォリオ":
    render_portfolio_fixed(st, storage)
    st.stop()

# ここから先は従来の「トレーニング」ページ
parent_view = st.toggle("親ビュー（集計）", value=False)

selected_date = st.date_input("日付を選択", value=date.today(), key="train_date")
weekday_idx = selected_date.weekday()
weekday_key = WEEKDAY_KEYS[weekday_idx]
weekday_jp = WEEKDAY_JP[weekday_idx]

day_key = DAY_PLAN.get(weekday_key, "OFF")
st.write(f"{weekday_jp}曜日｜メニュー：{DAY_TITLE.get(day_key, day_key)}")

with st.expander("共通ルール（必読）", expanded=True):
    for r in COMMON_RULES:
        st.write(f"・{r}")

# ======================
# 毎日（共通）
# ======================
render_daily(st, storage, selected_date, weekday_key)

st.divider()

# ======================
# OFF or DAYトレ
# ======================
if day_key == "OFF":
    render_box_breath_ui(st, key_prefix=f"box_{selected_date}_OFF")
    st.divider()
    st.info("今日はOFF（回復日）です。**ストレッチ10〜15分だけは必ず**やりましょう。")
else:
    render_day_training(st, storage, selected_date, weekday_key, day_key, train_df)

    st.divider()
    render_weight(st, storage, selected_date, weekday_key)

# ======================
# 親ビュー（集計）
# ======================
if parent_view:
    st.divider()
    render_parent_view(st, storage)
