# modules/ui_parent_view.py

import pandas as pd
import altair as alt


def _try_get_records_df(storage):
    """
    storage実装差異に強い取得。
    取れない場合でも例外で落とさず None を返す。
    """
    candidates = [
        "load_all_records",          # ✅ これを追加（今回の本命）
        "get_all_records_df",
        "read_all_records_df",
        "get_records_df",
        "read_records_df",
        "get_all_records",
        "read_all_records",
        "get_records",
        "read_records",
    ]

    for name in candidates:
        if hasattr(storage, name):
            try:
                obj = getattr(storage, name)()
                if obj is None:
                    continue
                if isinstance(obj, pd.DataFrame):
                    return obj.copy()
                if isinstance(obj, list):
                    return pd.DataFrame(obj)
            except Exception:
                continue

    return None


def render_parent_view(st, storage):
    st.header("親ビュー（集計）")

    df = _try_get_records_df(storage)
    if df is None or df.empty:
        st.warning("記録データが取得できませんでした（Sheets/CSVの読み込み結果を確認してください）。")
        return

    if "date" not in df.columns:
        st.warning("記録に 'date' カラムが見つかりません。")
        return

    st.subheader("体重推移")

    if "weight" not in df.columns:
        st.info("まだ体重の記録がありません。")
        return

    w = df[["date", "weight"]].copy()
    w["date"] = pd.to_datetime(w["date"], errors="coerce")
    w["weight"] = pd.to_numeric(w["weight"], errors="coerce")
    w = w.dropna(subset=["date", "weight"]).sort_values("date")

    if w.empty:
        st.info("体重の数値データがありません。")
        return

    y_min = 40.0
    y_max = float(max(w["weight"].max(), y_min + 1.0))

    chart = (
        alt.Chart(w)
        .mark_line(point=True)
        .encode(
            x=alt.X("date:T", title="日付"),
            y=alt.Y("weight:Q", title="体重(kg)", scale=alt.Scale(domain=[y_min, y_max])),
            tooltip=[alt.Tooltip("date:T", title="日付"), alt.Tooltip("weight:Q", title="体重(kg)")],
        )
        .properties(height=320)
    )

    st.altair_chart(chart, use_container_width=True)
