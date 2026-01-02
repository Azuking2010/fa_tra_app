from datetime import date as date_type

def render_weight(st, storage, selected_date: date_type, weekday_key: str):
    st.subheader("体重（kg）")
    weight = st.number_input("今日の体重", min_value=30.0, max_value=90.0, step=0.1)

    if st.button("体重を保存"):
        d_str = selected_date.strftime("%Y-%m-%d")
        row = {
            "date": d_str,
            "weekday": weekday_key,
            "day": "WEIGHT",
            "item": "weight",
            "part": "body",
            "done": True,
            "weight": float(weight),
        }
        storage.append_records([row])
        st.success("体重を保存しました！")
