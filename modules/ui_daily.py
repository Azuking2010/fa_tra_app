from datetime import date as date_type
import pandas as pd

from modules.constants import DAILY_REQUIRED, DAILY_OPTIONAL_BY_WEEKDAY
from modules.metronome_component import render_metronome_ui


def _calc_streak_days_from_latest_training(storage) -> int:
    """
    直近のトレーニング日（体重除外・done=Trueが1つでもある日）から遡って連続日数を計算する。
    今日やっていなくても、最後にやった日を起点にカウントする仕様。
    """
    try:
        df = storage.load_all_records()
    except Exception:
        return 0

    if df is None or df.empty:
        return 0

    # 必須カラムチェック
    for c in ["date", "day", "done"]:
        if c not in df.columns:
            return 0

    d = df.copy()

    # date整形
    d["date"] = pd.to_datetime(d["date"], errors="coerce").dt.date
    d = d.dropna(subset=["date"])

    # done整形（Sheets/CSVの差異吸収）
    d["done"] = d["done"].astype(str).str.lower().isin(["true", "1", "yes", "y"])

    # 体重は除外、done=Trueのみ
    d = d[(d["done"] == True) & (d["day"] != "WEIGHT")]

    if d.empty:
        return 0

    # 実施日集合
    days = sorted(set(d["date"].tolist()))
    if not days:
        return 0

    # 起点：直近の実施日
    cur = days[-1]
    streak = 1

    # 直近日から1日ずつ遡って存在する限りカウント
    day_set = set(days)
    while True:
        prev = cur.fromordinal(cur.toordinal() - 1)  # cur - 1 day（date型で安全に）
        if prev in day_set:
            streak += 1
            cur = prev
        else:
            break

    return streak


def render_daily(st, storage, selected_date: date_type, weekday_key: str):
    # ✅ 子ビュー最上部：継続日数表示（体重は除外、直近トレ日から遡る）
    streak = _calc_streak_days_from_latest_training(storage)

    # コメント文（候補を差し替えたい場合はここだけ変更でOK）
    if streak > 0:
        st.markdown(f"### 🔥 **{streak}日継続中！この調子で頑張れ👍**")
    else:
        st.markdown("### 🌱 **今日からスタート！頑張れ👍**")

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
