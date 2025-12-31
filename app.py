# app.py
# ------------------------------------------------------------
# FA期間中のトレーニング記録（Google Sheets 版）
#
# - Streamlit Cloud の Secrets に、以下を設定している前提：
#   [gcp_service_account] ・・・サービスアカウントJSONの中身（TOML形式）
#   [sheets]
#   spreadsheet_id = "..."
#   worksheet_name = "log"
#
# - シート「log」には 1行目にヘッダ行があり、列名でマッピングします。
#   （ヘッダが無い/違う場合も、下の EXPECTED_COLUMNS に合わせて自動整形します）
#
# - trainings_list は assets/trainings_list/trainings_list.csv を参照（任意）
# ------------------------------------------------------------

import os
import datetime as dt
from typing import List, Dict, Any, Optional

import pandas as pd
import streamlit as st

# Google Sheets
import gspread
from google.oauth2.service_account import Credentials


# ========= 設定 =========
APP_TITLE = "FA期間中のトレーニング記録（Sheets版）"
TRAININGS_CSV_PATH = "assets/trainings_list/trainings_list.csv"

# 期待する列（Sheets側のヘッダ行として整形）
# 既にヘッダがある場合は、それに合わせて読みます。
EXPECTED_COLUMNS = [
    "date",          # YYYY-MM-DD
    "weekday",       # Mon/Tue...
    "week_id",       # ISO week number
    "rec_id",        # 連番
    "day",           # 任意（Day1 等）
    "weight",        # 体重
    "trainings",     # 選択したメニュー（|区切り）
    "memo",          # メモ
    "timestamp",     # 保存時刻（ISO）
]


# ========= ユーティリティ =========
def iso_week_id(d: dt.date) -> int:
    return int(d.isocalendar().week)

def weekday_str(d: dt.date) -> str:
    return d.strftime("%a")  # Mon, Tue...

def now_iso() -> str:
    return dt.datetime.now().replace(microsecond=0).isoformat(sep=" ")

def safe_float(x) -> Optional[float]:
    try:
        if x is None:
            return None
        s = str(x).strip()
        if s == "":
            return None
        return float(s)
    except Exception:
        return None

def parse_date(x) -> Optional[dt.date]:
    if x is None:
        return None
    s = str(x).strip()
    if not s:
        return None
    # Google Sheets から date が datetime っぽく来る/文字列で来る両対応
    try:
        if isinstance(x, dt.date) and not isinstance(x, dt.datetime):
            return x
        if isinstance(x, dt.datetime):
            return x.date()
        return dt.date.fromisoformat(s[:10])
    except Exception:
        return None


# ========= Trainings CSV =========
@st.cache_data(show_spinner=False)
def load_trainings_master() -> List[str]:
    """
    assets/trainings_list/trainings_list.csv からメニュー一覧を読み込みます。
    形式は以下どれでもOK：
    - 1列だけ（列名あり/なし）
    - 'training' 列を含む
    """
    if not os.path.exists(TRAININGS_CSV_PATH):
        return []

    try:
        df = pd.read_csv(TRAININGS_CSV_PATH)
        if df.shape[1] == 0:
            return []
        # 列名が training の場合を優先
        if "training" in df.columns:
            items = df["training"].dropna().astype(str).tolist()
        else:
            # 先頭列を採用
            items = df.iloc[:, 0].dropna().astype(str).tolist()
        # 空/重複除去
        items = [x.strip() for x in items if str(x).strip()]
        items = sorted(list(dict.fromkeys(items)))
        return items
    except Exception:
        return []


# ========= Google Sheets 接続 =========
def get_gspread_client() -> gspread.Client:
    """
    st.secrets["gcp_service_account"] を使って gspread クライアントを作成
    """
    if "gcp_service_account" not in st.secrets:
        raise RuntimeError("Streamlit Secrets に [gcp_service_account] が見つかりません。")

    sa_info = dict(st.secrets["gcp_service_account"])

    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive",
    ]
    creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
    return gspread.authorize(creds)

def open_worksheet() -> gspread.Worksheet:
    if "sheets" not in st.secrets:
        raise RuntimeError("Streamlit Secrets に [sheets] が見つかりません。")
    spreadsheet_id = st.secrets["sheets"].get("spreadsheet_id")
    worksheet_name = st.secrets["sheets"].get("worksheet_name", "log")
    if not spreadsheet_id:
        raise RuntimeError("Secrets の [sheets].spreadsheet_id が空です。")

    gc = get_gspread_client()
    sh = gc.open_by_key(spreadsheet_id)
    ws = sh.worksheet(worksheet_name)
    return ws

def ensure_header(ws: gspread.Worksheet, expected_cols: List[str]) -> List[str]:
    """
    1行目がヘッダならそれを返す。空なら expected_cols を書き込む。
    ヘッダが一部欠けている場合は「既存 + 追加」で揃える。
    """
    first_row = ws.row_values(1)
    if not first_row or all(str(x).strip() == "" for x in first_row):
        ws.update("A1", [expected_cols])
        return expected_cols

    header = [str(x).strip() for x in first_row]
    # 既存ヘッダが expected を満たさない場合は追記して揃える
    missing = [c for c in expected_cols if c not in header]
    if missing:
        new_header = header + missing
        ws.update("A1", [new_header])
        return new_header
    return header

@st.cache_data(show_spinner=False, ttl=15)
def fetch_logs() -> pd.DataFrame:
    """
    Sheets から全行を DataFrame で取得（ヘッダ行込み）。
    """
    ws = open_worksheet()
    header = ensure_header(ws, EXPECTED_COLUMNS)

    values = ws.get_all_values()
    if len(values) <= 1:
        return pd.DataFrame(columns=header)

    df = pd.DataFrame(values[1:], columns=header)

    # 型整形
    if "date" in df.columns:
        df["date"] = df["date"].apply(parse_date)
    if "week_id" in df.columns:
        df["week_id"] = pd.to_numeric(df["week_id"], errors="coerce").astype("Int64")
    if "rec_id" in df.columns:
        df["rec_id"] = pd.to_numeric(df["rec_id"], errors="coerce").astype("Int64")
    if "weight" in df.columns:
        df["weight"] = df["weight"].apply(safe_float)

    # 並び
    if "date" in df.columns:
        df = df.sort_values(by=["date", "rec_id"], ascending=[False, False], na_position="last")

    return df

def get_next_rec_id(df: pd.DataFrame) -> int:
    if df is None or df.empty or "rec_id" not in df.columns:
        return 1
    s = df["rec_id"].dropna()
    if s.empty:
        return 1
    try:
        return int(s.max()) + 1
    except Exception:
        return 1

def append_log_row(row: Dict[str, Any]) -> None:
    ws = open_worksheet()
    header = ensure_header(ws, EXPECTED_COLUMNS)

    # ヘッダ順に並べて追記
    out = []
    for col in header:
        v = row.get(col, "")
        # date を YYYY-MM-DD に
        if isinstance(v, dt.date):
            v = v.isoformat()
        out.append("" if v is None else str(v))
    ws.append_row(out, value_input_option="USER_ENTERED")


# ========= UI =========
st.set_page_config(page_title=APP_TITLE, layout="wide")
st.title(APP_TITLE)

with st.sidebar:
    st.subheader("設定 / 状態")
    st.caption("Sheets から読み書きします。エラーが出たら Secrets/共有権限を確認。")

    # 接続チェック
    ok = True
    try:
        _ws = open_worksheet()
        st.success("Google Sheets 接続OK")
        st.caption(f"sheet: {_ws.title}")
    except Exception as e:
        ok = False
        st.error("Google Sheets 接続NG")
        st.code(str(e))

    st.divider()
    st.subheader("メニュー一覧（CSV）")
    trainings_master = load_trainings_master()
    if trainings_master:
        st.caption(f"{len(trainings_master)} 件読み込み")
    else:
        st.caption("CSVが無い/読めない場合は手入力でもOK")


if not ok:
    st.stop()

# データ取得
df = fetch_logs()
next_id = get_next_rec_id(df)

# タブ
tab_add, tab_view, tab_weight = st.tabs(["➕ 記録する", "📋 履歴を見る", "📈 体重推移"])

# ========== 記録する ==========
with tab_add:
    col1, col2 = st.columns([1, 1], gap="large")

    with col1:
        st.subheader("基本情報")
        d = st.date_input("日付", value=dt.date.today())
        weekday = weekday_str(d)
        week_id = iso_week_id(d)

        st.text_input("曜日（自動）", value=weekday, disabled=True)
        st.number_input("week_id（自動: ISO週）", value=int(week_id), step=1, disabled=True)

        rec_id = st.number_input("rec_id（自動）", value=int(next_id), step=1)
        day_label = st.text_input("day（任意）", value="")

        weight = st.number_input("体重（kg）", value=0.0, step=0.1, format="%.1f")

    with col2:
        st.subheader("トレーニング内容")
        if trainings_master:
            selected = st.multiselect("メニュー（複数選択）", trainings_master)
            trainings_text = " | ".join(selected)
            st.text_input("trainings（保存形式）", value=trainings_text, disabled=True)
        else:
            trainings_text = st.text_input("trainings（自由入力）", value="")

        memo = st.text_area("memo（任意）", value="", height=180)

        st.divider()
        if st.button("✅ 保存（Sheetsに追記）", type="primary", use_container_width=True):
            row = {
                "date": d.isoformat(),
                "weekday": weekday,
                "week_id": week_id,
                "rec_id": rec_id,
                "day": day_label,
                "weight": weight if weight > 0 else "",
                "trainings": trainings_text,
                "memo": memo,
                "timestamp": now_iso(),
            }
            try:
                append_log_row(row)
                # キャッシュ更新
                fetch_logs.clear()
                st.success("保存しました！")
                st.rerun()
            except Exception as e:
                st.error("保存に失敗しました")
                st.code(str(e))

# ========== 履歴を見る ==========
with tab_view:
    st.subheader("記録一覧")

    # フィルタ
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        from_date = st.date_input("From", value=(dt.date.today() - dt.timedelta(days=30)))
    with c2:
        to_date = st.date_input("To", value=dt.date.today())
    with c3:
        kw = st.text_input("キーワード（trainings/memo）", value="")

    view_df = df.copy()
    if "date" in view_df.columns:
        view_df = view_df[view_df["date"].notna()]
        view_df = view_df[(view_df["date"] >= from_date) & (view_df["date"] <= to_date)]

    if kw.strip():
        k = kw.strip().lower()
        cols = [c for c in ["trainings", "memo"] if c in view_df.columns]
        if cols:
            mask = False
            for c in cols:
                mask = mask | view_df[c].fillna("").astype(str).str.lower().str.contains(k)
            view_df = view_df[mask]

    st.dataframe(view_df, use_container_width=True, height=520)

    st.caption("※ 編集・削除は安全のためこの版では未実装（必要なら実装するよ）。")

# ========== 体重推移 ==========
with tab_weight:
    st.subheader("体重推移（入力がある日だけ）")
    if df.empty or "date" not in df.columns or "weight" not in df.columns:
        st.info("体重データがまだありません。")
    else:
        wdf = df[["date", "weight"]].copy()
        wdf = wdf[wdf["date"].notna()]
        wdf = wdf[wdf["weight"].notna()]
        wdf = wdf.sort_values("date", ascending=True)

        if wdf.empty:
            st.info("体重が入力された行がありません。")
        else:
            st.line_chart(wdf.set_index("date")["weight"])

            # 最新
            latest = wdf.iloc[-1]
            st.metric("最新の体重", f"{latest['weight']:.1f} kg", help=f"日付: {latest['date']}")
