from datetime import date as date_type
from modules.constants import DAILY_REQUIRED, DAILY_OPTIONAL_BY_WEEKDAY
from modules.metronome_component import render_metronome_ui

def render_daily(st, storage, selected_date: date_type, weekday_key: str):
    st.header("毎日（共通）")

    daily_optional = DAILY_OPTIONAL_BY_WEEKDAY.get(weekday_key)
    daily_rows = []
    daily_rows.extend(DAILY_REQUIRED)
    if daily_optional:
        daily_rows.append(daily_optional)

    # 縄跳びのときだけメトロノームUIを出す
    is_rope_day = daily_optional and ("縄跳び" in daily_optional.get("name", "")) and (weekday_key in ["wed", "sat"])

    with st.form(key=f"form_daily_{selected_date}"):
        daily_checks = {}

        for item in daily_rows:
            name = item["name"]
            part = item["part"]
            tip = item.get("tip", "")

            badge = "【必須】" if item in DAILY_REQUIRED else "【任意】"
            st.subheader(f"{badge} {name}")
            if tip:
                st.write(f"注意：{tip}")

            # 縄跳びの日だけ「リズム機能」案内
            if is_rope_day and ("縄跳び" in name):
                with st.expander("リズム機能を使う（60秒×3セット推奨）", expanded=False):
                    render_metronome_ui(st, key_prefix=f"rope_{selected_date}")

            daily_checks[name] = {
                "done": st.checkbox("やった", value=False, key=f"chk_{selected_date}_DAILY_{name}"),
                "part": part,
            }
            st.divider()

        daily_submitted = st.form_submit_button("毎日メニューを保存")

    if daily_submitted:
        rows = []
        d_str = selected_date.strftime("%Y-%m-%d")

        # ✅ done=True のものだけ追記（ログが汚れない）
        for name, v in daily_checks.items():
            if v["done"]:
                rows.append({
                    "date": d_str,
                    "weekday": weekday_key,
                    "day": "DAILY",
                    "item": name,
                    "part": v["part"],
                    "done": True,
                    "weight": "",
                })

        storage.append_records(rows)
        st.success("毎日メニューを保存しました！")
