import json
import os
from datetime import date
import pandas as pd
import streamlit as st

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
</style>
""", unsafe_allow_html=True)

DATA_PATH = "data.csv"
MENU_PATH = "menus.json"

WEEKDAY_KEYS = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]

# ======================
# 関数
# ======================
def load_menus():
    with open(MENU_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_data():
    if not os.path.exists(DATA_PATH):
        df = pd.DataFrame(columns=["date", "weekday", "menu", "item", "category", "done", "weight"])
        df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

def load_data():
    ensure_data()
    try:
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    except Exception:
        # 壊れてたら作り直す
        try:
            os.remove(DATA_PATH)
        except Exception:
            pass
        ensure_data()
        df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")

    if "date" in df.columns and not df.empty:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
    return df

def save_data(df):
    df.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")

def item_text(item: dict) -> str:
    for k in ["point", "tips", "note", "desc", "description"]:
        v = item.get(k)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""

def upsert_done_row(df: pd.DataFrame, d: date, weekday_key: str, menu_key: str, name: str, cat: str, done: bool):
    """同じ日付×メニュー×種目が既にあれば上書き、なければ追加"""
    d_str = d.strftime("%Y-%m-%d")

    # date列がdatetimeのときもあるので、比較用に文字列列を作る
    df2 = df.copy()
    if "date" in df2.columns and not df2.empty:
        # datetime→str
        df2["date_str"] = pd.to_datetime(df2["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    else:
        df2["date_str"] = []

    mask = (df2["date_str"] == d_str) & (df2["menu"] == menu_key) & (df2["item"] == name)

    if mask.any():
        # 上書き
        idx = df2[mask].index[0]
        df.loc[idx, "date"] = d_str
        df.loc[idx, "weekday"] = weekday_key
        df.loc[idx, "menu"] = menu_key
        df.loc[idx, "item"] = name
        df.loc[idx, "category"] = cat
        df.loc[idx, "done"] = bool(done)
        # weightは触らない
    else:
        new_row = {
            "date": d_str,
            "weekday": weekday_key,
            "menu": menu_key,
            "item": name,
            "category": cat,
            "done": bool(done),
            "weight": None
        }
        df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

    return df

# ======================
# データロード
# ======================
menus = load_menus()
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

menu_key = menus.get("week", {}).get(weekday_key, "OFF")
st.write(f"{weekday_jp}曜日｜メニュー：{menu_key}")

# ----------------------
# メニュー表示（子ども側）
# ----------------------
if menu_key != "OFF":
    menu = menus["menus"][menu_key]

    st.header(menu.get("title", f"メニュー {menu_key}"))
    if menu.get("goal"):
        st.caption(menu["goal"])

    # フォーム内でチェック→保存ボタン
    with st.form(key=f"form_{selected_date}_{menu_key}"):
        checks = {}
        for item in menu.get("items", []):
            name = item.get("name", "（名称未設定）")
            sets = item.get("set", "")
            cat = item.get("category", "")

            st.subheader(f"{name}（{sets}）" if sets else name)

            txt = item_text(item)
            if txt:
                st.write(txt)

            # ★ここ重要：デフォルトは必ずOFF（保存済みでもONにしない）
            checks[name] = {
                "done": st.checkbox("やった", value=False, key=f"chk_{selected_date}_{menu_key}_{name}"),
                "category": cat
            }
            st.divider()

        submitted = st.form_submit_button("このメニューを保存")

    if submitted:
        # まとめて保存（upsertで二重登録防止）
        for name, v in checks.items():
            df = upsert_done_row(
                df=df,
                d=selected_date,
                weekday_key=weekday_key,
                menu_key=menu_key,
                name=name,
                cat=v["category"],
                done=v["done"]
            )
        save_data(df)
        st.success("保存しました！")

    st.divider()

    # 体重入力（こちらも保存ボタン式）
    st.subheader("体重（kg）")
    weight = st.number_input("今日の体重", min_value=30.0, max_value=90.0, step=0.1)

    if st.button("体重を保存"):
        d_str = selected_date.strftime("%Y-%m-%d")

        df2 = df.copy()
        if not df2.empty and "date" in df2.columns:
            df2["date_str"] = pd.to_datetime(df2["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        else:
            df2["date_str"] = []

        mask = (df2["date_str"] == d_str) & (df2["menu"] == "weight") & (df2["item"] == "weight")
        if mask.any():
            idx = df2[mask].index[0]
            df.loc[idx, "date"] = d_str
            df.loc[idx, "weekday"] = weekday_key
            df.loc[idx, "menu"] = "weight"
            df.loc[idx, "item"] = "weight"
            df.loc[idx, "category"] = "body"
            df.loc[idx, "done"] = True
            df.loc[idx, "weight"] = float(weight)
        else:
            new_row = {
                "date": d_str,
                "weekday": weekday_key,
                "menu": "weight",
                "item": "weight",
                "category": "body",
                "done": True,
                "weight": float(weight)
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

    st.header("トレ実施数（カテゴリ別）")
    if not df.empty and "category" in df.columns:
        cat_df = df[df["done"] == True].groupby("category").size()
        if not cat_df.empty:
            st.bar_chart(cat_df)
        else:
            st.info("まだトレ記録がありません。")
    else:
        st.info("まだトレ記録がありません。")
