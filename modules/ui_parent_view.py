import pandas as pd
import altair as alt

def _get_all_records_df(storage):
    """
    storageの実装差を吸収して、全レコードDataFrameを取得する。
    """
    # よくある候補を順に試す（今後storage側を変えても壊れにくい）
    for fn in ["get_records_df", "load_records_df", "read_all_df", "read_df", "to_df", "fetch_df", "get_df"]:
        if hasattr(storage, fn):
            df = getattr(storage, fn)()
            if isinstance(df, pd.DataFrame):
                return df

    # append_recordsしているので、最低限これが無いと困る：read_all()
    if hasattr(storage, "read_all"):
        rows = storage.read_all()
        return pd.DataFrame(rows)

    raise RuntimeError("storageからレコードDataFrameを取得できませんでした（storage側のAPI名が想定外です）。")


def render_parent_view(st, storage):
    st.header("体重推移")

    df = _get_all_records_df(storage)

    # 想定列が無い/空のときでも落とさない
    if df is None or df.empty or ("weight" not in df.columns):
        st.info("まだ体重データがありません。")
        st.header("トレ実施数（部位別）")
        st.info("まだトレ記録がありません。")
        return

    # 体重だけ抽出
    w = df.copy()
    if "date" in w.columns:
        w["date"] = pd.to_datetime(w["date"], errors="coerce")
    w["weight"] = pd.to_numeric(w["weight"], errors="coerce")

    w = w.dropna(subset=["date", "weight"]).sort_values("date")

    if w.empty:
        st.info("まだ体重データがありません。")
    else:
        # ✅ Y軸の最小を40kgに固定（要望）
        y_min = 40
        y_max = float(w["weight"].max())
        # 上限は自動で少し余白（最低でも y_min+5）
        y_max = max(y_min + 5, y_max + 1)

        chart = (
            alt.Chart(w)
            .mark_line(point=True)
            .encode(
                x=alt.X("date:T", title="日付"),
                y=alt.Y("weight:Q", title="体重(kg)", scale=alt.Scale(domain=[y_min, y_max])),
                tooltip=[
                    alt.Tooltip("date:T", title="日付"),
                    alt.Tooltip("weight:Q", title="体重(kg)"),
                ],
            )
            .properties(height=320)
        )
        st.altair_chart(chart, use_container_width=True)

    st.header("トレ実施数（部位別）")

    # done=Trueだけ数える（無い場合も落とさない）
    if "done" not in df.columns:
        st.info("まだトレ記録がありません。")
        return

    done_df = df[df["done"] == True].copy()

    if done_df.empty or ("part" not in done_df.columns):
        st.info("まだトレ記録がありません。")
        return

    part_counts = done_df.groupby("part").size().reset_index(name="count")
    if part_counts.empty:
        st.info("まだトレ記録がありません。")
        return

    bar = (
        alt.Chart(part_counts)
        .mark_bar()
        .encode(
            x=alt.X("part:N", title="部位"),
            y=alt.Y("count:Q", title="回数"),
            tooltip=[alt.Tooltip("part:N", title="部位"), alt.Tooltip("count:Q", title="回数")],
        )
        .properties(height=280)
    )
    st.altair_chart(bar, use_container_width=True)
