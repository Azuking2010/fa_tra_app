import os
import json
from datetime import date
import pandas as pd
import streamlit as st
from urllib.parse import urlparse, parse_qs

# ===== Sheets =====
import gspread
from google.oauth2.service_account import Credentials

# ======================
# ページ設定
# ======================
st.set_page_config(page_title="FA期間 自主トレチェック", layout="centered")

# ======================
# CSS（文字サイズ調整）
# ======================
st.markdown(
    """
<style>
html, body, [class*="css"]  { font-size: 20px !important; }
h1 { font-size: 40px !important; }
h2 { font-size: 30px !important; }
h3 { font-size: 24px !important; }
label, p, li, div { font-size: 20px !important; }
a, button { font-size: 20px !important; }
</style>
""",
    unsafe_allow_html=True,
)

# ======================
# パス（ローカルCSV：Sheets NG時のフォールバック用）
# ======================
DATA_PATH = "data.csv"
TRAININGS_DIR = "assets/trainings_list"
TRAININGS_CSV_PATH = os.path.join(TRAININGS_DIR, "trainings_list.csv")   # CSV優先
TRAININGS_XLSX_PATH = os.path.join(TRAININGS_DIR, "trainings_list.xlsx")  # 予備

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# ======================
# 週間メニュー
# ======================
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
    "OFF": "OFF（ストレッチのみ）",
}

# Excel/CSVの「部位」→DAYへの割当
PART_TO_DAY = {
    "背筋": "BACK",
    "背中＋胸": "BACK",
    "胸": "CHEST",
    "腹筋＋体幹": "CORE",
    "横腹": "CORE",
    "体幹＋横腹": "CORE",
}

# ======================
# 共通ルール
# ======================
COMMON_RULES = [
    "各種目：12回 × 3セット（基本）",
    "休憩：30〜45秒",
    "テンポ：引っ張るときはできるだけ速く／戻すときは2秒かけてゆっくり",
    "反動は使わない",
    "必須は必ず実施。選択から追加して合計3〜4種目",
]

# 種目ごとの注意点
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
# 毎日（共通）
# ======================
DAILY_REQUIRED = [
    {"name": "ボールタッチ（5分）", "part": "毎日・ボール", "tip": "軽めでOK。感覚維持が目的。"},
]

DAILY_OPTIONAL_BY_WEEKDAY = {
    "mon": {"name": "ストレッチ（10〜15分）", "part": "毎日・回復", "tip": "頑張らない。回復優先。"},
    "tue": {"name": "軽めラン（10分）", "part": "毎日・刺激", "tip": "息が上がらない強度で。"},
    "wed": {"name": "縄跳び（3分）", "part": "毎日・刺激", "tip": "リズムよく。無理に追い込まない。"},
    "thu": {"name": "散歩（10分）", "part": "毎日・回復", "tip": "回復目的。気分転換でOK。"},
    "fri": {"name": "軽めラン（10分）", "part": "毎日・刺激", "tip": "疲労を残さないペースで。"},
    "sat": {"name": "縄跳び（3分）", "part": "毎日・刺激", "tip": "短くOK。体を温める程度。"},
    "sun": {"name": "散歩（10分）", "part": "毎日・回復", "tip": "回復優先。"},
}

# ======================
# YouTube URL処理
# ======================
def extract_youtube_id(url: str) -> str:
    if not isinstance(url, str) or not url.strip():
        return ""
    u = url.strip()
    try:
        parsed = urlparse(u)
    except Exception:
        return ""
    host = (parsed.netloc or "").lower()
    path = parsed.path or ""

    if "youtu.be" in host:
        return path.lstrip("/").split("/")[0]

    if "youtube.com" in host:
        qs = parse_qs(parsed.query)
        if "v" in qs and len(qs["v"]) > 0:
            return qs["v"][0]
        if "/embed/" in path:
            return path.split("/embed/")[-1].split("/")[0]
        if "/shorts/" in path:
            return path.split("/shorts/")[-1].split("/")[0]
    return ""

def build_youtube_urls(url: str, start_sec: int) -> dict:
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
# 記録データ定義
# ======================
RECORD_COLUMNS = ["date", "weekday", "day", "item", "part", "done", "weight"]

def normalize_record_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=RECORD_COLUMNS)

    df2 = df.copy()

    # 旧列名救済
    if "day" not in df2.columns and "menu" in df2.columns:
        df2.rename(columns={"menu": "day"}, inplace=True)
    if "part" not in df2.columns and "category" in df2.columns:
        df2.rename(columns={"category": "part"}, inplace=True)

    # 欠け列補完
    for c in RECORD_COLUMNS:
        if c not in df2.columns:
            df2[c] = None

    # 型
    try:
        df2["done"] = df2["done"].astype("bool", errors="ignore")
    except Exception:
        pass
    df2["weight"] = pd.to_numeric(df2["weight"], errors="coerce")
    df2["date"] = pd.to_datetime(df2["date"], errors="coerce")

    return df2[RECORD_COLUMNS]

# ======================
# 種目マスタ読み込み（CSV優先）
# ======================
@st.cache_data(show_spinner=False)
def load_training_list() -> pd.DataFrame:
    if not os.path.exists(TRAININGS_CSV_PATH) and not os.path.exists(TRAININGS_XLSX_PATH):
        return pd.DataFrame(
            columns=["種目名", "部位", "動画LINK", "動画開始時間(sec)", "必須/選択",
                     "DAY", "is_required", "video_embed_url", "video_watch_url"]
        )

    if os.path.exists(TRAININGS_CSV_PATH):
        try:
            df = pd.read_csv(TRAININGS_CSV_PATH, encoding="utf-8-sig")
        except Exception:
            df = pd.read_csv(TRAININGS_CSV_PATH, encoding="utf-8")
    else:
        df = pd.read_excel(TRAININGS_XLSX_PATH)

    for col in ["種目名", "部位", "動画LINK", "動画開始時間(sec)", "必須/選択"]:
        if col not in df.columns:
            df[col] = ""

    df = df.dropna(subset=["種目名"]).copy()
    df["種目名"] = df["種目名"].astype(str).str.strip()
    df["部位"] = df["部位"].astype(str).str.strip()
    df["動画LINK"] = df["動画LINK"].astype(str).str.strip()
    df["必須/選択"] = df["必須/選択"].astype(str).str.strip()
    df["動画開始時間(sec)"] = pd.to_numeric(df["動画開始時間(sec)"], errors="coerce").fillna(0).astype(int)

    df["DAY"] = df["部位"].map(PART_TO_DAY).fillna("OTHER")
    df["is_required"] = df["必須/選択"].isin(["必須", "Required", "REQ"])
    df.loc[df["DAY"] == "CHEST", "is_required"] = True  # CHESTは全部必須

    def _urls(row):
        d = build_youtube_urls(row["動画LINK"], row["動画開始時間(sec)"])
        return pd.Series([d["embed_url"], d["watch_url"]])

    df[["video_embed_url", "video_watch_url"]] = df.apply(_urls, axis=1)
    return df

# ======================
# Sheets 接続・入出力
# ======================
SHEETS_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

def _get_service_account_info():
    """
    st.secrets の形式揺れを吸収して service_account dict を返す。
    例:
      [gcp_service_account] type="service_account" ... 形式
    """
    if "gcp_service_account" not in st.secrets:
        raise KeyError("Secrets に [gcp_service_account] がありません")

    info = st.secrets["gcp_service_account"]

    # もし JSON 文字列で入ってた場合
    if isinstance(info, str):
        info = json.loads(info)

    # private_key が \n のままの時は復元
    if isinstance(info, dict) and "private_key" in info and isinstance(info["private_key"], str):
        info["private_key"] = info["private_key"].replace("\\n", "\n")

    return info

@st.cache_resource(show_spinner=False)
def _connect_gspread():
    info = _get_service_account_info()
    creds = Credentials.from_service_account_info(info, scopes=SHEETS_SCOPES)
    client = gspread.authorize(creds)
    return client

def _get_sheet_ids():
    if "sheets" not in st.secrets:
        raise KeyError("Secrets に [sheets] がありません（spreadsheet_id / worksheet_name）")
    ssid = st.secrets["sheets"].get("spreadsheet_id", "").strip()
    wname = st.secrets["sheets"].get("worksheet_name", "").strip()
    if not ssid:
        raise ValueError("spreadsheet_id が空です")
    if not wname:
        raise ValueError("worksheet_name が空です")
    return ssid, wname

def _open_worksheet(create_if_missing: bool = True):
    client = _connect_gspread()
    ssid, wname = _get_sheet_ids()

    # 404 対策：キーで開けない場合は URL/ID ミス or 共有不足の可能性大
    sh = client.open_by_key(ssid)

    try:
        ws = sh.worksheet(wname)
    except Exception:
        if not create_if_missing:
            raise
        ws = sh.add_worksheet(title=wname, rows=2000, cols=20)
        # ヘッダー行を作る
        ws.update([RECORD_COLUMNS])
    return ws

def _sheet_to_df(ws) -> pd.DataFrame:
    values = ws.get_all_values()
    if not values:
        return pd.DataFrame(columns=RECORD_COLUMNS)

    header = values[0]
    rows = values[1:]

    # ヘッダーが想定外なら作り直しに近い処理（落とさない）
    if header != RECORD_COLUMNS:
        # 可能なら header を優先して読み込む
        df = pd.DataFrame(rows, columns=header)
    else:
        df = pd.DataFrame(rows, columns=RECORD_COLUMNS)

    # done/weight/date の型を整える
    if "done" in df.columns:
        df["done"] = df["done"].astype(str).str.lower().isin(["true", "1", "yes", "y", "t"])
    if "weight" in df.columns:
        df["weight"] = pd.to_numeric(df["weight"], errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    return normalize_record_df(df)

def _df_to_sheet(ws, df: pd.DataFrame):
    df = normalize_record_df(df)

    out = df.copy()
    # date を文字列保存
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out["done"] = out["done"].fillna(False).astype(bool)

    values = [RECORD_COLUMNS] + out[RECORD_COLUMNS].astype(str).values.tolist()

    ws.clear()
    ws.update(values)

# ======================
# ローカルCSV（フォールバック）
# ======================
def ensure_data_local():
    if not os.path.exists(DATA_PATH):
        pd.DataFrame(columns=RECORD_COLUMNS).to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

def load_data_local():
    ensure_data_local()
    try:
        raw = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    except Exception:
        raw = pd.read_csv(DATA_PATH, encoding="utf-8")
    return normalize_record_df(raw)

def save_data_local(df: pd.DataFrame):
    out = normalize_record_df(df).copy()
    out["date"] = pd.to_datetime(out["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    out.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

# ======================
# ストレージ抽象化（Sheets優先・NGならCSV）
# ======================
class Storage:
    def __init__(self):
        self.mode = "CSV"
        self.ws = None
        self.last_error = None

    def connect(self):
        try:
            self.ws = _open_worksheet(create_if_missing=True)
            # 軽く読めるか確認
            _ = self.ws.row_values(1)
            self.mode = "SHEETS"
            self.last_error = None
        except Exception as e:
            self.mode = "CSV"
            self.ws = None
            self.last_error = e

    def load(self) -> pd.DataFrame:
        if self.mode == "SHEETS" and self.ws is not None:
            return _sheet_to_df(self.ws)
        return load_data_local()

    def save(self, df: pd.DataFrame):
        if self.mode == "SHEETS" and self.ws is not None:
            _df_to_sheet(self.ws, df)
        else:
            save_data_local(df)

storage = Storage()
storage.connect()

# ======================
# 便利：Upsert
# ======================
def upsert_done_row(df: pd.DataFrame, d: date, weekday_key: str, day_key: str, name: str, part: str, done: bool):
    df = normalize_record_df(df)
    d_str = d.strftime("%Y-%m-%d")

    df2 = df.copy()
    df2["date_str"] = pd.to_datetime(df2["date"], errors="coerce").dt.strftime("%Y-%m-%d")
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

    return normalize_record_df(df)

def upsert_weight(df: pd.DataFrame, d: date, weekday_key: str, weight_val: float):
    df = normalize_record_df(df)
    d_str = d.strftime("%Y-%m-%d")

    df2 = df.copy()
    df2["date_str"] = pd.to_datetime(df2["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    mask = (df2["date_str"] == d_str) & (df2["day"] == "WEIGHT") & (df2["item"] == "weight")

    if mask.any():
        idx = df2[mask].index[0]
        df.loc[idx, "date"] = d_str
        df.loc[idx, "weekday"] = weekday_key
        df.loc[idx, "day"] = "WEIGHT"
        df.loc[idx, "item"] = "weight"
        df.loc[idx, "part"] = "body"
        df.loc[idx, "done"] = True
        df.loc[idx, "weight"] = float(weight_val)
    else:
        new_row = {
            "date": d_str,
            "weekday": weekday_key,
            "day": "WEIGHT",
            "item": "weight",
            "part": "body",
            "done": True,
            "weight": float(weight_val),
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    return normalize_record_df(df)

def get_saved_done(df: pd.DataFrame, d: date, day_key: str, item_name: str) -> bool:
    df = normalize_record_df(df)
    d_str = d.strftime("%Y-%m-%d")
    df2 = df.copy()
    df2["date_str"] = pd.to_datetime(df2["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    mask = (df2["date_str"] == d_str) & (df2["day"] == day_key) & (df2["item"] == item_name)
    if mask.any():
        v = df2.loc[df2[mask].index[0], "done"]
        return bool(v)
    return False

def get_saved_weight(df: pd.DataFrame, d: date):
    df = normalize_record_df(df)
    d_str = d.strftime("%Y-%m-%d")
    df2 = df.copy()
    df2["date_str"] = pd.to_datetime(df2["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    mask = (df2["date_str"] == d_str) & (df2["day"] == "WEIGHT") & (df2["item"] == "weight")
    if mask.any():
        v = df2.loc[df2[mask].index[0], "weight"]
        try:
            return float(v)
        except Exception:
            return None
    return None

# ======================
# データロード
# ======================
train_df = load_training_list()
df = storage.load()

# ======================
# サイドバー：接続状態
# ======================
with st.sidebar:
    st.subheader("設定 / 状態")
    st.write("Sheets から読み書きします。エラーが出たら Secrets/共有権限 を確認。")

    if storage.mode == "SHEETS":
        st.success("Google Sheets 接続OK")
        try:
            ssid, wname = _get_sheet_ids()
            st.caption(f"spreadsheet_id: {ssid}")
            st.caption(f"worksheet: {wname}")
        except Exception:
            pass
    else:
        st.error("Google Sheets 接続NG（CSVにフォールバック）")
        if storage.last_error is not None:
            st.code(str(storage.last_error))

    st.divider()
    st.subheader("メニュー一覧（CSV）")
    st.caption(f"{len(train_df)} 件読み込み")

# ======================
# UI（ここから：更新前の形を維持）
# ======================
st.title("FA期間 自主トレチェック")

parent_view = st.toggle("親ビュー（集計）", value=False)

selected_date = st.date_input("日付を選択", value=date.today())
weekday_idx = selected_date.weekday()
weekday_key = WEEKDAY_KEYS[weekday_idx]
weekday_jp = WEEKDAY_JP[weekday_idx]

day_key = DAY_PLAN.get(weekday_key, "OFF")
st.write(f"{weekday_jp}曜日｜メニュー：{DAY_TITLE.get(day_key, day_key)}")

with st.expander("共通ルール（必読）", expanded=True):
    for r in COMMON_RULES:
        st.write(f"・{r}")

# ======================
# 毎日（共通）
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

        default_done = get_saved_done(df, selected_date, "DAILY", name)

        daily_checks[name] = {
            "done": st.checkbox("やった", value=default_done, key=f"chk_{selected_date}_DAILY_{name}"),
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
    storage.save(df)
    st.success("毎日メニューを保存しました！")

st.divider()

# OFF
if day_key == "OFF":
    st.info("今日はOFF（回復日）です。**ストレッチ10〜15分だけは必ず**やりましょう。")

# トレ表示
if day_key != "OFF":
    today_items = train_df[train_df["DAY"] == day_key].copy()

    if today_items.empty:
        st.error("このDAYに該当する種目がマスタにありません。マスタの「部位」表記を確認してください。")
    else:
        st.header(DAY_TITLE.get(day_key, day_key))

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

                if embed_url and is_youtube_url(watch_url or embed_url):
                    st.video(embed_url)
                    if watch_url:
                        st.link_button("▶ YouTubeで開く（指定秒から）", watch_url)
                elif watch_url:
                    st.link_button("▶ 動画/解説を見る（外部リンク）", watch_url)

                default_done = get_saved_done(df, selected_date, day_key, name)

                checks[name] = {
                    "done": st.checkbox("やった", value=default_done, key=f"chk_{selected_date}_{day_key}_{name}"),
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
            storage.save(df)
            st.success("保存しました！")

        st.divider()

        with st.expander("他の候補（今日はやらなくてOK）", expanded=False):
            if optional_df.empty:
                st.write("（選択候補なし）")
            else:
                for _, r in optional_df.iterrows():
                    st.write(f"・{r['種目名']}（{r['部位']}）")

    # 体重入力（保存済みがあれば初期値に反映）
    st.subheader("体重（kg）")
    saved_w = get_saved_weight(df, selected_date)
    init_w = saved_w if saved_w is not None else 55.0

    weight = st.number_input("今日の体重", min_value=30.0, max_value=90.0, step=0.1, value=float(init_w))

    if st.button("体重を保存"):
        df = upsert_weight(df, selected_date, weekday_key, float(weight))
        storage.save(df)
        st.success("体重を保存しました！")

# 親ビュー（集計）
if parent_view:
    st.divider()
    st.header("体重推移")

    df = normalize_record_df(df)
    weight_df = df.dropna(subset=["weight"]).copy()
    if not weight_df.empty:
        weight_df["date"] = pd.to_datetime(weight_df["date"], errors="coerce")
        weight_df = weight_df.dropna(subset=["date"]).sort_values("date")
        st.line_chart(weight_df.set_index("date")["weight"])
    else:
        st.info("まだ体重データがありません。")

    st.header("トレ実施数（部位別）")
    done_df = df[df["done"] == True].copy()
    if not done_df.empty:
        part_df = done_df.groupby("part").size()
        if not part_df.empty:
            st.bar_chart(part_df)
        else:
            st.info("まだトレ記録がありません。")
    else:
        st.info("まだトレ記録がありません。")
