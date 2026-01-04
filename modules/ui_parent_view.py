import pandas as pd
import altair as alt


def render_parent_view(st, storage):
    st.header("親ビュー（集計）")

    # --- 全件読み込み ---
    try:
        df = storage.load_all_records()
    except Exception as e:
        st.warning(f"記録データが取得できませんでした：{e}")
        return

    if df is None or df.empty:
        st.warning("記録データがありません。")
        return

    # 必要カラムが無いケースにも耐える
    for c in ["date", "day", "done", "part"]:
        if c not in df.columns:
            st.warning(f"記録に '{c}' カラムが見つかりません。")
            return

    d = df.copy()
    d["date"] = pd.to_datetime(d["date"], errors="coerce")
    d = d.dropna(subset=["date"])
    d["done"] = d["done"].astype(str).str.lower().isin(["true", "1", "yes", "y"])

    # --- 体重推移 ---
    st.subheader("体重推移")

    if "weight" not in d.columns:
        st.info("まだ体重の記録がありません。")
    else:
        w = d[["date", "weight"]].copy()
        w["weight"] = pd.to_numeric(w["weight"], errors="coerce")
        w = w.dropna(subset=["weight"]).sort_values("date")

        if w.empty:
            st.info("体重の数値データがありません。")
        else:
            # ✅ 仕様fix：下限45kg / 上限=最新体重+5kg
            y_min = 45.0
            latest_weight = float(w.iloc[-1]["weight"])
            y_max = float(max(latest_weight + 5.0, y_min + 1.0))  # 念のため逆転防止

            chart_w = (
                alt.Chart(w)
                .mark_line(point=True)
                .encode(
                    x=alt.X("date:T", title="日付"),
                    y=alt.Y("weight:Q", title="体重(kg)", scale=alt.Scale(domain=[y_min, y_max])),
                    tooltip=[
                        alt.Tooltip("date:T", title="日付"),
                        alt.Tooltip("weight:Q", title="体重(kg)")
                    ],
                )
                .properties(height=320)
            )
            st.altair_chart(chart_w, use_container_width=True)

    # --- トレ実施（部位別 積み上げ） ---
    st.subheader("トレ実施数（部位別・積み上げ）")

    # done=True だけ、体重は除外
    done_df = d[(d["done"] == True) & (d["day"] != "WEIGHT")].copy()

    if done_df.empty:
        st.info("まだトレ記録がありません。")
        return

    # 日付（YYYY-MM-DD）に丸めて集計
    done_df["date_day"] = done_df["date"].dt.date.astype(str)

    # part が空の行は "Unknown" に寄せる（落ちないように）
    done_df["part"] = done_df["part"].fillna("Unknown").replace("", "Unknown")

    agg = done_df.groupby(["date_day", "part"]).size().reset_index(name="count")

    # 日付順に見えるようソートキー
    date_order = sorted(agg["date_day"].unique().tolist())

    chart_p = (
        alt.Chart(agg)
        .mark_bar()
        .encode(
            x=alt.X("date_day:N", title="日付", sort=date_order),
            y=alt.Y("count:Q", title="実施数"),
            color=alt.Color("part:N", title="部位"),
            tooltip=[
                alt.Tooltip("date_day:N", title="日付"),
                alt.Tooltip("part:N", title="部位"),
                alt.Tooltip("count:Q", title="回数"),
            ],
        )
        .properties(height=360)
    )

    st.altair_chart(chart_p, use_container_width=True)
