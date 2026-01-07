import streamlit as st
from datetime import date

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
# helper（最新の「値」を拾う）
#  - 0は「無効値（空白と同等）」として扱う
# ======================
def _is_blank_like(v):
    if v is None:
        return True
    if isinstance(v, str):
        s = v.strip()
        return s == "" or s.lower() in ["nan", "none"]
    if isinstance(v, (int, float)):
        try:
            return float(v) == 0.0
        except Exception:
            return False
    return False


def _latest_non_empty(df, col):
    """
    末尾から遡って、最初に見つかった「空でない値」を返す。
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
            if vv.lower() in ["nan", "none"]:
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
            if fv == 0.0:
                continue
            return fv
        return None
    except Exception:
        # 念のため
        s2 = s.dropna()
        if s2.empty:
            return None
        # 最後が0の可能性があるので遡る
        for v in reversed(s2.tolist()):
            try:
                if float(v) != 0.0:
                    return v
            except Exception:
                continue
        return None


def _latest_bool(df, col):
    v = _latest_non_empty(df, col)
    if v is None:
        # boolは 0扱いではないので、ここは False をデフォルト
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ["true", "1", "yes", "y", "on"]


def _prev_caption(st, v):
    """前回値：表示（0/空は表示しない）"""
    if _is_blank_like(v):
        return
    st.caption(f"前回値：{v}")


def _num_default(v, fallback=0.0):
    """前回値をデフォルトに入れる（0/空ならfallback=0）"""
    if _is_blank_like(v):
        return float(fallback)
    try:
        return float(v)
    except Exception:
        return float(fallback)


def _text_default(v, fallback=""):
    if v is None:
        return fallback
    s = str(v).strip()
    if s == "" or s.lower() in ["nan", "none"]:
        return fallback
    return s


# ======================
# portfolio UI（固定入力）
#  - checkbox廃止
#  - 0は保存しない（空白扱い）
#  - 前回値表示
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

    # 既存データ（最新値の初期値に使う）
    dfp = storage.load_all_portfolio()

    # date は UI の日付を使う
    st.markdown("### ① 基本")
    selected_date = st.date_input("日付", value=date.today(), key="pf_date")

    # ----------------------
    # ② 体（身長/体重）
    # ----------------------
    st.markdown("### ② 体（body）")
    c1, c2 = st.columns(2)

    default_height = _latest_non_empty(dfp, "height_cm")
    default_weight = _latest_non_empty(dfp, "weight_kg")

    height_cm = c1.number_input(
        "身長 (cm)",
        min_value=0.0,
        max_value=250.0,
        value=_num_default(default_height, 0.0),
        step=0.1,
        key="pf_height_cm",
    )
    _prev_caption(c1, default_height)

    weight_kg = c2.number_input(
        "体重 (kg)",
        min_value=0.0,
        max_value=200.0,
        value=_num_default(default_weight, 0.0),
        step=0.1,
        key="pf_weight_kg",
    )
    _prev_caption(c2, default_weight)

    # BMI 表示（保存は Sheets 側計算でもOK）
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
    default_100 = _latest_non_empty(dfp, "run_100m_sec")
    default_1500 = _latest_non_empty(dfp, "run_1500m_sec")
    default_3000 = _latest_non_empty(dfp, "run_3000m_sec")
    default_meet = _latest_non_empty(dfp, "track_meet")

    cc1, cc2, cc3 = st.columns(3)
    run_100 = cc1.number_input(
        "100m (sec)",
        min_value=0.0,
        max_value=9999.0,
        value=_num_default(default_100, 0.0),
        step=0.01,
        key="pf_run_100",
    )
    _prev_caption(cc1, default_100)

    run_1500 = cc2.number_input(
        "1500m (sec)",
        min_value=0.0,
        max_value=99999.0,
        value=_num_default(default_1500, 0.0),
        step=0.1,
        key="pf_run_1500",
    )
    _prev_caption(cc2, default_1500)

    run_3000 = cc3.number_input(
        "3000m (sec)",
        min_value=0.0,
        max_value=99999.0,
        value=_num_default(default_3000, 0.0),
        step=0.1,
        key="pf_run_3000",
    )
    _prev_caption(cc3, default_3000)

    track_meet = st.text_input(
        "陸上大会名（任意）",
        value=_text_default(default_meet, ""),
        key="pf_track_meet",
    )

    # ----------------------
    # ④ 学業（テスト）
    # ----------------------
    st.markdown("### ④ 学業（school）")
    default_rank = _latest_non_empty(dfp, "rank")
    default_dev = _latest_non_empty(dfp, "deviation")
    default_jp = _latest_non_empty(dfp, "score_jp")
    default_math = _latest_non_empty(dfp, "score_math")
    default_en = _latest_non_empty(dfp, "score_en")
    default_sci = _latest_non_empty(dfp, "score_sci")
    default_soc = _latest_non_empty(dfp, "score_soc")
    default_rating = _latest_non_empty(dfp, "rating")

    s1, s2, s3 = st.columns(3)
    rank = s1.number_input(
        "順位 (rank)",
        min_value=0.0,
        max_value=99999.0,
        value=_num_default(default_rank, 0.0),
        step=1.0,
        key="pf_rank",
    )
    _prev_caption(s1, default_rank)

    deviation = s2.number_input(
        "偏差値 (deviation)",
        min_value=0.0,
        max_value=100.0,
        value=_num_default(default_dev, 0.0),
        step=0.1,
        key="pf_deviation",
    )
    _prev_caption(s2, default_dev)

    rating = s3.number_input(
        "評点 (rating)",
        min_value=0.0,
        max_value=999.0,
        value=_num_default(default_rating, 0.0),
        step=0.1,
        key="pf_rating",
    )
    _prev_caption(s3, default_rating)

    t1, t2, t3, t4, t5 = st.columns(5)
    score_jp = t1.number_input(
        "国語",
        min_value=0.0,
        max_value=200.0,
        value=_num_default(default_jp, 0.0),
        step=1.0,
        key="pf_score_jp",
    )
    _prev_caption(t1, default_jp)

    score_math = t2.number_input(
        "数学",
        min_value=0.0,
        max_value=200.0,
        value=_num_default(default_math, 0.0),
        step=1.0,
        key="pf_score_math",
    )
    _prev_caption(t2, default_math)

    score_en = t3.number_input(
        "英語",
        min_value=0.0,
        max_value=200.0,
        value=_num_default(default_en, 0.0),
        step=1.0,
        key="pf_score_en",
    )
    _prev_caption(t3, default_en)

    score_sci = t4.number_input(
        "理科",
        min_value=0.0,
        max_value=200.0,
        value=_num_default(default_sci, 0.0),
        step=1.0,
        key="pf_score_sci",
    )
    _prev_caption(t4, default_sci)

    score_soc = t5.number_input(
        "社会",
        min_value=0.0,
        max_value=200.0,
        value=_num_default(default_soc, 0.0),
        step=1.0,
        key="pf_score_soc",
    )
    _prev_caption(t5, default_soc)

    # ----------------------
    # ⑤ サッカー（実績）
    # ----------------------
    st.markdown("### ⑤ サッカー（soccer）")
    default_tcenter = _latest_bool(dfp, "tcenter")
    default_soc_tour = _latest_non_empty(dfp, "soccer_tournament")
    default_match = _latest_non_empty(dfp, "match_result")
    default_url = _latest_non_empty(dfp, "video_url")
    default_vnote = _latest_non_empty(dfp, "video_note")

    tcenter = st.checkbox("トレセン（tcenter）", value=default_tcenter, key="pf_tcenter")

    soccer_tournament = st.text_input(
        "サッカー大会名（任意）",
        value=_text_default(default_soc_tour, ""),
        key="pf_soccer_tournament",
    )

    match_result = st.text_input(
        "試合実績（match_result）",
        value=_text_default(default_match, ""),
        key="pf_match_result",
    )

    v1, v2 = st.columns(2)
    video_url = v1.text_input(
        "動画URL（video_url）",
        value=_text_default(default_url, ""),
        key="pf_video_url",
    )
    video_note = v2.text_input(
        "動画備考（video_note）",
        value=_text_default(default_vnote, ""),
        key="pf_video_note",
    )

    # ----------------------
    # ⑥ 自由記述
    # ----------------------
    st.markdown("### ⑥ 自由記述（note）")
    default_note = _latest_non_empty(dfp, "note")
    note = st.text_area(
        "メモ（note）",
        value=_text_default(default_note, ""),
        height=120,
        key="pf_note",
    )

    st.divider()

    # ======================
    # 保存（行追加）
    # ルール：
    # - 数値は「0なら保存しない（空白扱い）」
    # - 文字列は空なら保存しない
    # - tcenter は履歴として残すため常に保存（False/True）
    # - bmi は基本保存しない（Sheets数式運用）
    # ======================
    if st.button("保存（行追加）", type="primary", use_container_width=True):
        row = {"date": str(selected_date)}

        # 数値：0は保存しない
        if height_cm != 0:
            row["height_cm"] = float(height_cm)
        if weight_kg != 0:
            row["weight_kg"] = float(weight_kg)

        # bmi：保存しない（Sheets側の式でOK）
        # if bmi_preview is not None:
        #     row["bmi"] = float(bmi_preview)

        if run_100 != 0:
            row["run_100m_sec"] = float(run_100)
        if run_1500 != 0:
            row["run_1500m_sec"] = float(run_1500)
        if run_3000 != 0:
            row["run_3000m_sec"] = float(run_3000)

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

        # tcenter は常に保存（False/True）
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

        # 事故防止：date 以外に何も無い場合は保存しない
        meaningful = [k for k in row.keys() if k not in ["date"]]
        if len(meaningful) == 0:
            st.warning("保存する値がありません（全て空欄）")
        else:
            storage.append_portfolio_row(row)
            st.success("保存しました（行追加）")
            st.caption("※集計側は『最新行』ではなく、列ごとに最新『値』を採用してください")


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
        # portfolio は表示だけ（無い場合もある）
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
    # ★月曜OFFのおまけ（ボックスブリージング）
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
