from datetime import date as date_type
import pandas as pd

from modules.constants import DAY_TITLE, EX_TIPS
from modules.youtube_utils import is_youtube_url
from modules.breath_component import render_breath_ui


def render_day_training(st, storage, selected_date: date_type, weekday_key: str, day_key: str, train_df: pd.DataFrame):
    today_items = train_df[train_df["DAY"] == day_key].copy()

    if today_items.empty:
        st.error("このDAYに該当する種目がマスタにありません。マスタの「部位」表記を確認してください。")
        return

    st.header(DAY_TITLE.get(day_key, day_key))

    # 体幹DAY（CORE）の冒頭で呼吸法ガイドを表示（フォーム外）
    if day_key == "CORE":
        render_breath_ui(st, key_prefix=f"breath_{selected_date}_{day_key}")
        st.divider()

    required_df = today_items[today_items["is_required"]].copy()
    optional_df = today_items[~today_items["is_required"]].copy()

    optional_names = optional_df["種目名"].tolist()
    add_choice = None
    if len(optional_names) > 0:
        st.subheader("追加する種目（任意）")
        add_choice = st.selectbox(
            "今日は追加で1つやるなら選択（追加なしでもOK）",
            ["追加なし"] + optional_names,
            index=0,
        )

    display_rows = []

    # 必須を先に
    for _, r in required_df.iterrows():
        display_rows.append(r)

    # 追加は選んだ場合のみ1つ
    if add_choice and add_choice != "追加なし":
        add_r = optional_df[optional_df["種目名"] == add_choice]
        if not add_r.empty:
            display_rows.append(add_r.iloc[0])

    with st.form(key=f"form_{selected_date}_{day_key}"):
        checks = {}

        for r in display_rows:
            name = str(r["種目名"])
            part = str(r["部位"])
            tip = EX_TIPS.get(name, "")

            embed_url = str(r.get("video_embed_url", "")).strip()
            watch_url = str(r.get("video_watch_url", "")).strip()

            badge = "【必須】" if bool(r["is_required"]) else "【追加】"
            st.subheader(f"{badge} {name}")

            if tip:
                st.write(f"注意：{tip}")

            if embed_url and is_youtube_url(watch_url or embed_url):
                st.video(embed_url)
                if watch_url:
                    st.link_button("▶ YouTubeで開く（指定秒から）", watch_url)
            elif watch_url:
                st.link_button("▶ 動画/解説を見る（外部リンク）", watch_url)

            checks[name] = {
                "done": st.checkbox("やった", value=False, key=f"chk_{selected_date}_{day_key}_{name}"),
                "part": part,
            }

            st.divider()

        submitted = st.form_submit_button("このメニューを保存")

    if submitted:
        rows = []
        d_str = selected_date.strftime("%Y-%m-%d")

        # ✅ done=True のものだけ追記
        for name, v in checks.items():
            if v["done"]:
                rows.append({
                    "date": d_str,
                    "weekday": weekday_key,
                    "day": day_key,
                    "item": name,
                    "part": v["part"],
                    "done": True,
                    "weight": "",
                })

        storage.append_records(rows)
        st.success("保存しました！")

    with st.expander("他の候補（今日はやらなくてOK）", expanded=False):
        if optional_df.empty:
            st.write("（選択候補なし）")
        else:
            for _, r in optional_df.iterrows():
                st.write(f"・{r['種目名']}（{r['部位']}）")
