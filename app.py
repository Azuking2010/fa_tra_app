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
# ======================
def _latest_non_empty(df, col):
    if df is None or df.empty or col not in df.columns:
        return None
    s = df[col]
    # 文字列の空を除外
    if s.dtype == object:
        s2 = s.astype(str).replace("nan", "").replace("None", "")
        s2 = s2[s2.str.strip() != ""]
        if s2.empty:
            return None
        return s2.iloc[-1]
    # 数値
    s2 = s.dropna()
    if s2.empty:
        return None
    return s2.iloc[-1]


def _latest_bool(df, col):
    v = _latest_non_empty(df, col)
    if v is None:
        return False
    if isinstance(v, bool):
        return v
    return str(v).strip().lower() in ["true", "1", "yes", "y", "on"]


# ======================
# portfolio UI（固定入力）
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

    # ブロック ② 体（身長/体重）
    st.markdown("### ② 体（body）")
    c1, c2 = st.columns(2)

    default_height = _latest_non_empty(dfp, "height_cm")
    default_weight = _latest_non_empty(dfp, "weight_kg")

    height_cm = c1.number_input(
        "身長 (cm)",
        min_value=0.0,
        max_value=250.0,
        value=float(default_height) if default_height is not None else 0.0,
        step=0.1,
        key="pf_height_cm",
    )
    use_height = c1.checkbox("この値を使う（OFFなら空）", value=False, key="pf_use_height")

    weight_kg = c2.number_input(
        "体重 (kg)",
        min_value=0.0,
        max_value=200.0,
        value=float(default_weight) if default_weight is not None else 0.0,
        step=0.1,
        key="pf_weight_kg",
    )
    use_weight = c2.checkbox("この値を使う（OFFなら空）", value=False, key="pf_use_weight")

    # BMI 表示（保存は Sheets 側計算でもOK）
    bmi_preview = None
    if use_height and use_weight and height_cm > 0 and weight_kg > 0:
        bmi_preview = weight_kg / ((height_cm / 100.0) ** 2)
        st.caption(f"BMI（参考）: {bmi_preview:.2f}  ※保存はシート数式でもOK")

    # ブロック ③ 陸上（タイム）
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
        value=float(default_100) if default_100 is not None else 0.0,
        step=0.01,
        key="pf_run_100",
    )
    use_100 = cc1.checkbox("この値を使う（OFFなら空）", value=False, key="pf_use_100")

    run_1500 = cc2.number_input(
        "1500m (sec)",
        min_value=0.0,
        max_value=99999.0,
        value=float(default_1500) if default_1500 is not None else 0.0,
        step=0.1,
        key="pf_run_1500",
    )
    use_1500 = cc2.checkbox("この値を使う（OFFなら空）", value=False, key="pf_use_1500")

    run_3000 = cc3.number_input(
        "3000m (sec)",
        min_value=0.0,
        max_value=99999.0,
        value=float(default_3000) if default_3000 is not None else 0.0,
        step=0.1,
        key="pf_run_3000",
    )
    use_3000 = cc3.checkbox("この値を使う（OFFなら空）", value=False, key="pf_use_3000")

    track_meet = st.text_input(
        "陸上大会名（任意）",
        value=str(default_meet) if default_meet is not None else "",
        key="pf_track_meet",
    )

    # ブロック ④ 学業（テスト）
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
        value=float(default_rank) if default_rank is not None else 0.0,
        step=1.0,
        key="pf_rank",
    )
    use_rank = s1.checkbox("この値を使う（OFFなら空）", value=False, key="pf_use_rank")

    deviation = s2.number_input(
        "偏差値 (deviation)",
        min_value=0.0,
        max_value=100.0,
        value=float(default_dev) if default_dev is not None else 0.0,
        step=0.1,
        key="pf_deviation",
    )
    use_deviation = s2.checkbox("この値を使う（OFFなら空）", value=False, key="pf_use_deviation")

    rating = s3.number_input(
        "評点 (rating)",
        min_value=0.0,
        max_value=999.0,
        value=float(default_rating) if default_rating is not None else 0.0,
        step=0.1,
        key="pf_rating",
    )
    use_rating = s3.checkbox("この値を使う（OFFなら空）", value=False, key="pf_use_rating")

    t1, t2, t3, t4, t5 = st.columns(5)
    score_jp = t1.number_input("国語", min_value=0.0, max_value=200.0,
                               value=float(default_jp) if default_jp is not None else 0.0,
                               step=1.0, key="pf_score_jp")
    use_jp = t1.checkbox("使う", value=False, key="pf_use_jp")

    score_math = t2.number_input("数学", min_value=0.0, max_value=200.0,
                                 value=float(default_math) if default_math is not None else 0.0,
                                 step=1.0, key="pf_score_math")
    use_math = t2.checkbox("使う", value=False, key="pf_use_math")

    score_en = t3.number_input("英語", min_value=0.0, max_value=200.0,
                               value=float(default_en) if default_en is not None else 0.0,
                               step=1.0, key="pf_score_en")
    use_en = t3.checkbox("使う", value=False, key="pf_use_en")

    score_sci = t4.number_input("理科", min_value=0.0, max_value=200.0,
                                value=float(default_sci) if default_sci is not None else 0.0,
                                step=1.0, key="pf_score_sci")
    use_sci = t4.checkbox("使う", value=False, key="pf_use_sci")

    score_soc = t5.number_input("社会", min_value=0.0, max_value=200.0,
                                value=float(default_soc) if default_soc is not None else 0.0,
                                step=1.0, key="pf_score_soc")
    use_soc = t5.checkbox("使う", value=False, key="pf_use_soc")

    # ブロック ⑤ サッカー（実績）
    st.markdown("### ⑤ サッカー（soccer）")
    default_tcenter = _latest_bool(dfp, "tcenter")
    default_soc_tour = _latest_non_empty(dfp, "soccer_tournament")
    default_match = _latest_non_empty(dfp, "match_result")
    default_url = _latest_non_empty(dfp, "video_url")
    default_vnote = _latest_non_empty(dfp, "video_note")

    tcenter = st.checkbox("トレセン（tcenter）", value=default_tcenter, key="pf_tcenter")
    soccer_tournament = st.text_input(
        "サッカー大会名（任意）",
        value=str(default_soc_tour) if default_soc_tour is not None else "",
        key="pf_soccer_tournament",
    )
    match_result = st.text_input(
        "試合実績（match_result）",
        value=str(default_match) if default_match is not None else "",
        key="pf_match_result",
    )

    v1, v2 = st.columns(2)
    video_url = v1.text_input(
        "動画URL（video_url）",
        value=str(default_url) if default_url is not None else "",
        key="pf_video_url",
    )
    video_note = v2.text_input(
        "動画備考（video_note）",
        value=str(default_vnote) if default_vnote is not None else "",
        key="pf_video_note",
    )

    # ブロック ⑥ 自由記述
    st.markdown("### ⑥ 自由記述（note）")
    default_note = _latest_non_empty(dfp, "note")
    note = st.text_area(
        "メモ（note）",
        value=str(default_note) if default_note is not None else "",
        height=120,
        key="pf_note",
    )

    st.divider()

    # 保存（行追加）
    if st.button("保存（行追加）", type="primary", use_container_width=True):
        row = {"date": str(selected_date)}

        # 空白はスルー（B-1）
        if use_height:
            row["height_cm"] = float(height_cm)
        if use_weight:
            row["weight_kg"] = float(weight_kg)

        # bmi：ここは「保存しない（空）」を基本にする（Sheets数式運用向け）
        # もし app 側計算で保存したい場合は下を有効に:
        # if bmi_preview is not None:
        #     row["bmi"] = float(bmi_preview)

        if use_100:
            row["run_100m_sec"] = float(run_100)
        if use_1500:
            row["run_1500m_sec"] = float(run_1500)
        if use_3000:
            row["run_3000m_sec"] = float(run_3000)

        if str(track_meet).strip():
            row["track_meet"] = str(track_meet).strip()

        if use_rank:
            row["rank"] = float(rank)
        if use_deviation:
            row["deviation"] = float(deviation)
        if use_rating:
            row["rating"] = float(rating)

        if use_jp:
            row["score_jp"] = float(score_jp)
        if use_math:
            row["score_math"] = float(score_math)
        if use_en:
            row["score_en"] = float(score_en)
        if use_sci:
            row["score_sci"] = float(score_sci)
        if use_soc:
            row["score_soc"] = float(score_soc)

        # tcenter は値があるので常に入れる（False/True が履歴として残る）
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

        # 「date と tcenter だけ」みたいな保存もあり得るが、
        # 事故防止のため、ほぼ空の場合は警告
        meaningful = [k for k in row.keys() if k not in ["date"]]
        if len(meaningful) == 0:
            st.warning("保存する値がありません（全て空欄）")
        else:
            storage.append_portfolio_row(row)
            st.success("保存しました（行追加）")
            st.caption("※最新『行』ではなく、集計側では列ごとに最新『値』を採用してください")


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
