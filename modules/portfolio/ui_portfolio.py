from __future__ import annotations

from datetime import date as date_type
import pandas as pd
import streamlit as st

from .portfolio_models import PORTFOLIO_CATEGORIES, VISIBILITY_VALUES
from .portfolio_storage import PortfolioStorage
from .portfolio_utils import filter_by_days, latest_body_series


def render_portfolio(st, base_storage):
    st.header("ポートフォリオ（実績/成長記録）")

    pstore = PortfolioStorage(base_storage)

    # 接続チェック
    ok, msg = pstore.ensure_header()
    if not ok:
        st.error(msg)
        st.info("※いまは安全のため、portfolio は Sheets 接続時のみ有効にしています（CSV fallback では無効）。")
        return
    st.success("portfolio シートに接続OK")

    # ---------
    # 入力フォーム
    # ---------
    with st.expander("➕ 新規追加", expanded=True):
        with st.form("portfolio_add_form"):
            c1, c2 = st.columns([1, 1])

            with c1:
                d: date_type = st.date_input("日付", value=date_type.today())
                category = st.selectbox("カテゴリ", PORTFOLIO_CATEGORIES, index=0)
                metric = st.text_input("metric（例: 100m / height / tournament / grade_rank など）", value="")

            with c2:
                value_num = st.number_input("数値（value_num）※数値が無い場合は 0 にせず空扱いにします", value=0.0)
                use_value_num = st.checkbox("この数値を使う（OFFなら空）", value=False)
                value_text = st.text_input("文字（value_text）※補足や順位など", value="")

            unit = st.text_input("単位（unit）例: sec / cm / kg / 点 / 位 / 回戦", value="")
            title = st.text_input("表示名（title）例: 地区大会100m / トレセン選出 など", value="")
            tags = st.text_input("tags（任意：カンマ区切り）例: official,pb", value="")
            visibility = st.selectbox("公開範囲（visibility）", VISIBILITY_VALUES, index=0)
            url = st.text_input("URL（動画/証拠リンク 任意）", value="")
            memo = st.text_area("メモ（任意）", value="", height=120)

            submitted = st.form_submit_button("追加する")

        if submitted:
            if not metric.strip():
                st.error("metric は必須です（例: 100m / height / tournament 等）")
                return

            row = {
                "date": d.strftime("%Y-%m-%d"),
                "category": category,
                "metric": metric.strip(),
                "value_num": (float(value_num) if use_value_num else ""),
                "value_text": value_text.strip(),
                "unit": unit.strip(),
                "title": title.strip(),
                "tags": tags.strip(),
                "visibility": visibility,
                "url": url.strip(),
                "memo": memo.strip(),
                "created_at": "",
                "updated_at": "",
            }

            try:
                pstore.append_rows([row])
                st.success("追加しました！")
            except Exception as e:
                st.error(f"追加に失敗: {e}")

    st.divider()

    # ---------
    # 一覧 & フィルタ
    # ---------
    st.subheader("一覧 / フィルタ")

    range_label = st.selectbox("表示期間", ["7日", "30日", "90日", "180日", "全期間"], index=2)
    days_map = {"7日": 7, "30日": 30, "90日": 90, "180日": 180}

    try:
        df = pstore.load_df()
    except Exception as e:
        st.error(f"読み込みに失敗: {e}")
        return

    if df.empty:
        st.info("まだデータがありません。上の「新規追加」から入れてみて。")
        return

    if range_label != "全期間":
        df = filter_by_days(df, days_map[range_label])

    # 並び替え（date desc）
    if "date" in df.columns:
        df["_date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.sort_values("_date", ascending=False).drop(columns=["_date"], errors="ignore")

    st.dataframe(df, use_container_width=True, hide_index=True)

    st.divider()

    # ---------
    # 見える化（まずは body を最優先で）
    # ---------
    st.subheader("見える化（試作）")

    tab1, tab2 = st.tabs(["body（身長/体重/BMI）", "その他（後で拡張）"])

    with tab1:
        h = latest_body_series(df, "height")
        w = latest_body_series(df, "weight")
        b = latest_body_series(df, "bmi")

        colA, colB, colC = st.columns(3)
        with colA:
            st.markdown("### 身長（height）")
            if h.empty:
                st.info("height がまだ無いよ（category=body, metric=height, value_num=数値）")
            else:
                st.line_chart(h.set_index("date")["value_num"])
        with colB:
            st.markdown("### 体重（weight）")
            if w.empty:
                st.info("weight がまだ無いよ（category=body, metric=weight, value_num=数値）")
            else:
                st.line_chart(w.set_index("date")["value_num"])
        with colC:
            st.markdown("### BMI（bmi）")
            if b.empty:
                st.info("bmi がまだ無いよ（category=body, metric=bmi, value_num=数値）")
            else:
                st.line_chart(b.set_index("date")["value_num"])

        st.caption("※ まずは最小構成。次に track(100m/1500m) や study(順位) を追加していく想定。")

    with tab2:
        st.info("ここは次で拡張する（track/soccer/study/memo/video をカテゴリ別にグラフ・カード表示）")
