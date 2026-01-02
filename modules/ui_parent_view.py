import pandas as pd

def render_parent_view(st, storage):
    st.header("体重推移")

    df = storage.load_all_records()
    if df is None or df.empty:
        st.info("まだデータがありません。")
        return

    # 体重推移
    if "weight" in df.columns:
        weight_df = df.dropna(subset=["weight"]).copy()
        if not weight_df.empty:
            weight_df["date"] = pd.to_datetime(weight_df["date"], errors="coerce")
            weight_df = weight_df.dropna(subset=["date"]).sort_values("date")
            st.line_chart(weight_df.set_index("date")["weight"])
        else:
            st.info("まだ体重データがありません。")
    else:
        st.info("weight列が見つかりません。")

    st.header("トレ実施数（部位別）")

    # done==True のみ
    if "done" in df.columns:
        done_df = df[df["done"] == True].copy()
        if not done_df.empty and "part" in done_df.columns:
            part_df = done_df.groupby("part").size()
            if not part_df.empty:
                st.bar_chart(part_df)
            else:
                st.info("まだトレ記録がありません。")
        else:
            st.info("まだトレ記録がありません。")
    else:
        st.info("done列が見つかりません。")
