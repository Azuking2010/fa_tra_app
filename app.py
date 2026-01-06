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

# ★追加：月曜OFFで表示する用
from modules.box_breath_component import render_box_breath_ui

# ★追加：ポートフォリオページ
from modules.portfolio.ui_portfolio import render_portfolio


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
# Storage / Master
# ======================
storage = build_storage(st)                  # secrets があれば Sheets、なければ CSV
train_df = load_training_list()

# ======================
# UI
# ======================
st.title("FA期間 自主トレチェック")

# サイドバー：接続状態など + ページ切替
with st.sidebar:
    st.header("設定 / 状態")
    ok, msg = storage.healthcheck()
    if ok:
        st.success(msg)
    else:
        st.error(msg)

    # Sheetsのときだけ情報表示
    info = storage.get_info()
    if info:
        if "spreadsheet_id" in info:
            st.caption(f"spreadsheet_id:\n{info['spreadsheet_id']}")
        if "worksheet" in info:
            st.caption(f"worksheet: {info['worksheet']}")

    st.divider()

    # ★追加：ページ切替（安全にサイドバーへ）
    page = st.radio("ページ", ["トレーニング", "ポートフォリオ"], index=0)

# ======================
# ポートフォリオページ
# ======================
if page == "ポートフォリオ":
    render_portfolio(st, storage)
    st.stop()

# ======================
# ここから従来のトレーニング画面（現行維持）
# ======================

# 親ビュー
parent_view = st.toggle("親ビュー（集計）", value=False)

selected_date = st.date_input("日付を選択", value=date.today())
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
    # ★追加：月曜OFFのおまけ（ボックスブリージング）
    # ここは「OFFの日すべて」に出る仕様になる（＝月曜想定）
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
