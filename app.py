import os
from datetime import date
import pandas as pd
import streamlit as st
from urllib.parse import urlparse, parse_qs

# ======================
# ページ設定
# ======================
st.set_page_config(page_title="FA期間 自主トレチェック", layout="centered")

# ======================
# CSS（文字サイズ調整）
# ======================
st.markdown("""
<style>
html, body, [class*="css"]  { font-size: 20px !important; }
h1 { font-size: 40px !important; }
h2 { font-size: 30px !important; }
h3 { font-size: 24px !important; }
label, p, li, div { font-size: 20px !important; }
a, button { font-size: 20px !important; }
</style>
""", unsafe_allow_html=True)

DATA_PATH = "data.csv"
XLSX_PATH = "assets/trainings_list/trainings_list.xlsx"

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# ======================
# 週間メニュー（固定）
# ======================
# ★あなた指定のFA期間スケジュール
# 月：OFF（ストレッチのみ）
# 火：背中
# 水：腹
# 木：胸
# 金：背中
# 土：腹
# 日：胸
DAY_PLAN = {
    "mon": "OFF",
    "tue": "BACK",
    "wed": "CORE",
    "thu": "CHEST",
    "fri": "BACK",
    "sat": "CORE",
    "sun": "CHEST",
}

DAY_TITLE = {
    "BACK": "背中DAY（チューブ）",
    "CHEST": "胸DAY（チューブ）",
    "CORE": "腹・体幹DAY（チューブ）",
    "OFF": "OFF（休養）",
}

# Excelの「部位」→DAYへの割当
PART_TO_DAY = {
    "背筋": "BACK",
    "背中＋胸": "BACK",
    "胸": "CHEST",
    "腹筋＋体幹": "CORE",
    "横腹": "CORE",
    "体幹＋横腹": "CORE",
}

# ======================
# 共通ルール（UI表示用）
# ======================
COMMON_RULES = [
    "各種目：12回 × 3セット（基本）",
    "休憩：30〜45秒",
    "テンポ：引っ張るときはできるだけ速く／戻すときは2秒かけてゆっくり",
    "反動は使わない",
    "必須は必ず実施。選択から追加して合計3〜4種目",
]

# 種目ごとの「注意点（超短文）」
EX_TIPS = {
    "デッドリフト": "背中は一直線。腕で引かず、床を押すイメージ。",
    "シーテッドローイング": "肩をすくめない。肘を後ろへ引いて肩甲骨を寄せる。",
    "リバースシーテッドローイング": "肩をすくめない。肘を後ろへ、最後に肩甲骨。",
    "リバースフライズ": "腕だけでなく、肩甲骨を動かして横に開く。",
    "スクイーズバンド": "胸を張って背中を寄せる。首・肩に力を入れない。",
    "プッシュアップ": "体は一直線。腰が落ちないように体幹を固める。",
    "クロスオーバー": "胸を寄せる意識。肩が前に巻き込まれないように。",
    "チェストプレス": "肩をすくめない。胸を張って前へ押し出す。",
    "ニートゥチェスト": "反動NG。腹筋で膝を引き上げ、ゆっくり戻す。",
    "サイドベンド": "体を横に倒しすぎない。横腹に効かせて戻す。",
    "ウッドチョッパー": "体幹を固めて斜めに引き上げる。左右同じ回数。",
}

# ======================
# 毎日（共通）メニュー：A案
# ======================
DAILY_REQUIRED = [
    {"name": "ボールタッチ（5分）", "part": "毎日・ボール", "tip": "軽めでOK。感覚維持が目的。"},
]

# 日替わり（任意）…「飽き防止＋刺激程度」
DAILY_OPTIONAL_BY_WEEKDAY = {
    "mon": {"name": "縄跳び（3分）", "part": "毎日・刺激", "tip": "軽めでOK。フォーム重視。"},
    "tue": {"name": "軽めラン（10分）", "part": "毎日・刺激", "tip": "息が上がらない強度で。"},
    "wed": {"name": "縄跳び（3分）", "part": "毎日・刺激", "tip": "リズムよく。無理に追い込まない。"},
    "thu": {"name": "散歩（10分）", "part": "毎日・回復", "tip": "回復目的。気分転換でOK。"},
    "fri": {"name": "軽めラン（10分）", "part": "毎日・刺激", "tip": "疲労を残さないペースで。"},
    "sat": {"name": "縄跳び（3分）", "part": "毎日・刺激", "tip": "短くOK。体を温める程度。"},
    "sun": {"name": "散歩（10分）", "part": "毎日・回復", "tip": "回復優先。"},
}

# ======================
# YouTube URL処理（開始秒を確実化）
# ======================
def extract_youtube_id(url: str) -> str:
    """YouTubeのURLから動画IDを抽出。取れなければ空文字。"""
    if not isinstance(url, str) or not url.strip():
        return ""
    u = url.strip()

    try:
        parsed = urlparse(u)
    except Exception:
        return ""

    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    # youtu.be/VIDEO_ID
    if "youtu.be" in host:
        vid = path.lstrip("/").split("/")[0]
        return vid

    # youtube.com/watch?v=VIDEO_ID
    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        if "v" in qs and len(qs["v"]) > 0:
            return qs["v"][0]

        # /embed/VIDEO_ID
        if "/embed/" in path:
            return path.split("/embed/")[-1].split("/")[0]

        # /shorts/VIDEO_ID
        if "/shorts/" in path:
            return path.split("/shorts/")[-1].split("/")[0]

    return ""

def build_youtube_urls(url: str, start_sec: int) -> dict:
    """
    YouTubeなら
    - embed_url: st.videoで開始秒が効く形式
    - watch_url: 外部で開いても開始秒が効きやすい形式
    を返す。YouTubeでなければ元URLをwatch_urlに入れて返す。
    """
    vid = extract_youtube_id(url)
    s = int(start_sec) if start_sec and int(start_sec) > 0 else 0

    if not vid:
        return {"embed_url": "", "watch_url": (url or "").strip()}

    embed = f"https://www.youtube.com/embed/{vid}"
    watch = f"https://www.youtube.com/watch?v={vid}"

    if s > 0:
        embed = f"{embed}?start={s}"
        watch = f"{watch}&t={s}s"

    return {"embed_url": embed, "watch_url": watch}

def is_youtube_url(url: str) -> bool:
    return bool(extract_youtube_id(url))

# ======================
# 関数
# ======================
@st.cache_data(show_spinner=False)
def load_training_list() -> pd.DataFrame:
    """Excelから種目リストを読み込む（キャッシュ）"""
    if not os.path.exists(XLSX_PATH):
        return pd.DataFrame(columns=["種目名", "部位", "動画LINK", "動画開始時間(sec)", "必須/選択"])

    df = pd.read_excel(XLSX_PATH)

    # 想定列がないと落ちるので保険
    for col in ["種目名", "部位", "動画LINK", "動画開始時間(sec)", "必須/選択"]:
        if col not in df.columns:
            df[col] = ""

    # 空白行除去
    df = df.dropna(subset=["種目名"]).copy()
    df["種目名"] = df["種目名"].astype(str).str.strip()
    df["部位"] = df["部位"].astype(str).str.strip()
    df["動画LINK"] = df["動画LINK"].astype(str).str.strip()
    df["必須/選択"] = df["必須/選択"].astype(str).str.strip()

    # 開始秒を数値化（欠損は0）
    df["動画開始時間(sec)"] = pd.to_numeric(df["動画開始時間(sec)"], errors="coerce").fillna(0).astype(int)

    # DAY付与
    df["DAY"] = df["部位"].map(PART_TO_DAY).fillna("OTHER")

    # 必須判定（基本はExcelに従う）
    df["is_required"] = df["必須/選択"].isin(["必須", "Required", "REQ"])

    # ★CHESTは全部必須に強制（3種しかない想定）
    df.loc[df["DAY"] == "CHEST", "is_required"] = True

    # YouTube URL（embed/watch）を生成
    def _urls(row):
        d = build_youtube_urls(row["動画LINK"], row["動画開始時間(sec)"])
        return pd.Series([d["embed_url"], d["watch_url"]])

    df[["video_embed_url", "video_watch_url"]] = df.apply(_urls, axis=1)

    return df

def ensure_data():
    if not os.path.exists(DATA_PATH):
        df0 = pd.DataFrame(columns=["date", "weekday", "day", "item", "part", "done", "weight"])
        df0.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

def load_data():
    ensure_data()
    try:
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    except Exception:
        try:
            os.remove(DATA_PATH)
        except Exception:
            pass
        ensure_data()
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    if "date" in df.columns and not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

def save_data(df: pd.DataFrame):
    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

def upsert_done_row(df: pd.DataFrame, d: date, weekday_key: str, day_key: str, name: str, part: str, done: bool):
    """同じ日付×DAY×種目があれば上書き、なければ追加"""
    d_str = d.strftime("%Y-%m-%d")

    df2 = df.copy()
    if "date" in df2.columns and not df2.empty:
        df2["date_str"] = pd.to_datetime(df2["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        df2["date_str"] = []

    mask = (df2["date_str"] == d_str) & (df2["day"] == day_key) & (df2["item"] == name)

    if mask.any():
        idx = df2[mask].index[0]
        df.loc[idx, "date"] = d_str
        df.loc[idx, "weekday"] = weekday_key
        df.loc[idx, "day"] = day_key
        df.loc[idx, "item"] = name
        df.loc[idx, "part"] = part
        df.loc[idx, "done"] = bool(done)
    else:
        new_row = {
            "date": d_str,
            "weekday": weekday_key,
            "day": day_key,
            "item": name,
            "part": part,
            "done": bool(done),
            "weight": None,
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    return df

# ======================
# データロード
# ======================
train_df = load_training_list()
df = load_data()

# ======================
# UI
# ======================
st.title("FA期間 自主トレチェック")

parent_view = st.toggle("親ビュー（集計）", value=False)

selected_date = st.date_input("日付を選択", value=date.today())
weekday_idx = selected_date.weekday()
weekday_key = WEEKDAY_KEYS[weekday_idx]
weekday_jp = WEEKDAY_JP[weekday_idx]

day_key = DAY_PLAN.get(weekday_key, "OFF")
st.write(f"{weekday_jp}曜日｜メニュー：{DAY_TITLE.get(day_key, day_key)}")

# 共通ルール表示
with st.expander("共通ルール（必読）", expanded=True):
    for r in COMMON_RULES:
        st.write(f"・{r}")

# ======================
# 毎日（共通）欄：A案（必ず表示）
# ======================
st.header("毎日（共通）")

daily_optional = DAILY_OPTIONAL_BY_WEEKDAY.get(weekday_key)
daily_rows = []
daily_rows.extend(DAILY_REQUIRED)
if daily_optional:
    daily_rows.append(daily_optional)

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

        daily_checks[name] = {
            "done": st.checkbox("やった", value=False, key=f"chk_{selected_date}_DAILY_{name}"),
            "part": part,
        }
        st.divider()

    daily_submitted = st.form_submit_button("毎日メニューを保存")

if daily_submitted:
    for name, v in daily_checks.items():
        df = upsert_done_row(
            df=df,
            d=selected_date,
            weekday_key=weekday_key,
            day_key="DAILY",
            name=name,
            part=v["part"],
            done=v["done"],
        )
    save_data(df)
    st.success("毎日メニューを保存しました！")

st.divider()

# ----------------------
# OFF
# ----------------------
if day_key == "OFF":
    st.info("今日はトレーニングは休み（回復日）です。**ストレッチ10〜15分だけは必ず**やりましょう。")

# ----------------------
# トレ表示（子ども側）
# ----------------------
if day_key != "OFF":
    today_items = train_df[train_df["DAY"] == day_key].copy()

    if today_items.empty:
        st.error("このDAYに該当する種目がExcelにありません。Excelの「部位」表記を確認してください。")
    else:
        st.header(DAY_TITLE.get(day_key, day_key))

        required_df = today_items[today_items["is_required"]].copy()
        optional_df = today_items[~today_items["is_required"]].copy()

        # 追加種目を選ぶUI
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
        for _, r in required_df.iterrows():
            display_rows.append(r)

        if add_choice and add_choice != "追加なし":
            add_row = optional_df[optional_df["種目名"] == add_choice]
            if not add_row.empty:
                display_rows.append(add_row.iloc[0])

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

                # ★YouTubeは「埋め込みstart=」で確実に開始秒を効かせる
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
            for name, v in checks.items():
                df = upsert_done_row(
                    df=df,
                    d=selected_date,
                    weekday_key=weekday_key,
                    day_key=day_key,
                    name=name,
                    part=v["part"],
                    done=v["done"],
                )
            save_data(df)
            st.success("保存しました！")

        st.divider()

        # 参考：他の候補
        with st.expander("他の候補（今日はやらなくてOK）", expanded=False):
            if optional_df.empty:
                st.write("（選択候補なし）")
            else:
                for _, r in optional_df.iterrows():
                    st.write(f"・{r['種目名']}（{r['部位']}）")

    # 体重入力
    st.subheader("体重（kg）")
    weight = st.number_input("今日の体重", min_value=30.0, max_value=90.0, step=0.1)

    if st.button("体重を保存"):
        d_str = selected_date.strftime("%Y-%m-%d")

        df2 = df.copy()
        if not df2.empty and "date" in df2.columns:
            df2["date_str"] = pd.to_datetime(df2["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        else:
            df2["date_str"] = []

        mask = (df2["date_str"] == d_str) & (df2["day"] == "WEIGHT") & (df2["item"] == "weight")

        if mask.any():
            idx = df2[mask].index[0]
            df.loc[idx, "date"] = d_str
            df.loc[idx, "weekday"] = weekday_key
            df.loc[idx, "day"] = "WEIGHT"
            df.loc[idx, "item"] = "weight"
            df.loc[idx, "part"] = "body"
            df.loc[idx, "done"] = True
            df.loc[idx, "weight"] = float(weight)
        else:
            new_row = {
                "date": d_str,
                "weekday": weekday_key,
                "day": "WEIGHT",
                "item": "weight",
                "part": "body",
                "done": True,
                "weight": float(weight),
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        save_data(df)
        st.success("体重を保存しました！")

# ----------------------
# 親ビュー（集計）
# ----------------------
if parent_view:
    st.divider()
    st.header("体重推移")

    if not df.empty and "weight" in df.columns:
        weight_df = df.dropna(subset=["weight"]).copy()
        if not weight_df.empty:
            weight_df["date"] = pd.to_datetime(weight_df["date"], errors="coerce")
            weight_df = weight_df.dropna(subset=["date"]).sort_values("date")
            st.line_chart(weight_df.set_index("date")["weight"])
        else:
            st.info("まだ体重データがありません。")
    else:
        st.info("まだ体重データがありません。")

    st.header("トレ実施数（部位別）")
    if not df.empty and "part" in df.columns:
        part_df = df[df["done"] == True].groupby("part").size()
        if not part_df.empty:
            st.bar_chart(part_df)
        else:
            st.info("まだトレ記録がありません。")
    else:
        st.info("まだトレ記録がありません。")
