# app.py
# FA期間中のトレーニング記録 (Sheets版)
# - メニューは assets/trainings_list/trainings_list.csv から読み込み
# - 記録は Google Sheets に append（失敗時は画面に理由を出す）
# - Streamlit Secrets から service_account 情報と spreadsheet_id / worksheet_name を参照
#
# 必要パッケージ（requirements.txt）
# streamlit
# pandas
# gspread
# google-auth

from __future__ import annotations

import csv
import datetime as dt
import os
import re
from typing import Dict, List, Optional, Tuple

import pandas as pd
import streamlit as st

# Sheets
import gspread
from google.oauth2.service_account import Credentials


# -----------------------------
# 基本設定
# -----------------------------
APP_TITLE = "FA期間中のトレーニング記録（Sheets版）"
MENU_CSV_PATH = "assets/trainings_list/trainings_list.csv"

# Google Sheets API scope
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


# -----------------------------
# ユーティリティ
# -----------------------------
def _now_jst() -> dt.datetime:
    # Streamlit Cloud上ではUTCのことが多いので、表示だけJSTに寄せる
    # （サーバ時刻がJSTならそのままでもOK）
    return dt.datetime.utcnow() + dt.timedelta(hours=9)


def _safe_str(x) -> str:
    return "" if x is None else str(x)


def _load_menu_csv(path: str) -> pd.DataFrame:
    """
    trainings_list.csv を DataFrame で返す。
    想定列:
      - category / name / load / note ... など（何でもOK）
    最低限、name列（または training 等）があれば動くようにする。
    """
    if not os.path.exists(path):
        return pd.DataFrame(columns=["name"])

    # 文字化けしにくい順に試す
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            df = pd.read_csv(path, encoding=enc)
            if len(df.columns) == 0:
                continue
            return df
        except Exception:
            continue

    # 最後の手段
    return pd.DataFrame(columns=["name"])


def _menu_options(df: pd.DataFrame) -> List[str]:
    # よくある列名を吸収
    candidates = ["name", "training", "menu", "title"]
    col = None
    for c in candidates:
        if c in df.columns:
            col = c
            break
    if col is None:
        # 先頭列を名前扱い
        col = df.columns[0] if len(df.columns) else None

    if col is None:
        return []

    opts = []
    for v in df[col].fillna("").astype(str).tolist():
        v = v.strip()
        if v:
            opts.append(v)
    return opts


def _normalize_private_key(pk: str) -> str:
    """
    Streamlit Secretsの貼り方によっては以下の崩れが起きる：
    - \\n が文字として入っている（= 改行に戻す必要がある）
    - 余計なダブルクォートが混ざる
    - BEGIN/END周りに空白が混ざる
    それらをできるだけ修復する。
    """
    if pk is None:
        return ""

    pk = str(pk)

    # 余計な囲いが入ってたら除去
    pk = pk.strip().strip('"').strip("'")

    # literal \n を本当の改行へ
    pk = pk.replace("\\n", "\n")

    # BEGIN/END の前後に変な空白が入ることがあるので整形
    pk = re.sub(r"-----BEGIN PRIVATE KEY-----\s*", "-----BEGIN PRIVATE KEY-----\n", pk)
    pk = re.sub(r"\s*-----END PRIVATE KEY-----", "\n-----END PRIVATE KEY-----", pk)

    # 末尾改行が無いと嫌がるケースがあるので付ける
    if not pk.endswith("\n"):
        pk += "\n"

    return pk


def _build_service_account_info_from_secrets() -> Tuple[Optional[Dict], Optional[str]]:
    """
    st.secrets["gcp_service_account"] を from_service_account_info で使えるdictにする。
    失敗時は (None, エラー文字列) を返す。
    """
    if "gcp_service_account" not in st.secrets:
        return None, "st.secrets に [gcp_service_account] が見つかりません"

    info = dict(st.secrets["gcp_service_account"])

    # private_key を補正
    if "private_key" in info:
        info["private_key"] = _normalize_private_key(info["private_key"])

    # token_uri が無い場合に備える（JSONではだいたい入ってるが）
    info.setdefault("token_uri", "https://oauth2.googleapis.com/token")

    # 必須キーざっくりチェック
    required = ["type", "project_id", "private_key", "client_email", "token_uri"]
    missing = [k for k in required if not info.get(k)]
    if missing:
        return None, f"service_account 情報の必須キーが不足: {missing}"

    return info, None


@st.cache_resource(show_spinner=False)
def _get_gspread_client() -> Tuple[Optional[gspread.Client], Optional[str]]:
    """
    Secretsから認証して gspread client を返す。
    失敗時は (None, エラー文字列)
    """
    try:
        info, err = _build_service_account_info_from_secrets()
        if err:
            return None, err

        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        gc = gspread.authorize(creds)
        return gc, None

    except Exception as e:
        # Incorrect padding 等もここに出る
        return None, f"{type(e).__name__}: {e}"


def _get_sheet_params() -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    (spreadsheet_id, worksheet_name, err)
    """
    if "sheets" not in st.secrets:
        return None, None, "st.secrets に [sheets] が見つかりません"

    sheets_cfg = st.secrets["sheets"]
    spreadsheet_id = _safe_str(sheets_cfg.get("spreadsheet_id")).strip()
    worksheet_name = _safe_str(sheets_cfg.get("worksheet_name", "log")).strip()

    if not spreadsheet_id:
        return None, None, "sheets.spreadsheet_id が空です"
    if not worksheet_name:
        worksheet_name = "log"

    return spreadsheet_id, worksheet_name, None


def _open_or_create_worksheet(
    gc: gspread.Client,
    spreadsheet_id: str,
    worksheet_name: str,
) -> Tuple[Optional[gspread.Worksheet], Optional[str]]:
    """
    ワークシートを開く。無ければ作る。
    404/権限不足の時は原因が分かるメッセージを返す。
    """
    try:
        sh = gc.open_by_key(spreadsheet_id)
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        # 404の多くは「共有されてない」か「ID違い」
        hint = (
            "\n\n【対処】\n"
            "- spreadsheet_id が正しいか（URLの /d/ と /edit の間）\n"
            "- スプレッドシートをサービスアカウント（client_email）に『編集者』で共有したか\n"
        )
        return None, msg + hint

    try:
        ws = sh.worksheet(worksheet_name)
        return ws, None
    except gspread.WorksheetNotFound:
        # 無ければ作る
        try:
            ws = sh.add_worksheet(title=worksheet_name, rows=2000, cols=20)
            return ws, None
        except Exception as e:
            return None, f"{type(e).__name__}: {e}"


def _ensure_header(ws: gspread.Worksheet, header: List[str]) -> None:
    """
    1行目が空ならヘッダーを書く（既にあれば何もしない）
    """
    try:
        first_row = ws.row_values(1)
        if len([c for c in first_row if str(c).strip()]) == 0:
            ws.append_row(header, value_input_option="USER_ENTERED")
    except Exception:
        # ヘッダー失敗しても致命ではないので無視
        pass


def _append_log_row(ws: gspread.Worksheet, row: List[str]) -> Tuple[bool, str]:
    """
    append_row して成功/失敗を返す
    """
    try:
        ws.append_row(row, value_input_option="USER_ENTERED")
        return True, "OK"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _read_recent(ws: gspread.Worksheet, limit: int = 50) -> pd.DataFrame:
    """
    直近の行を読み込んでDataFrame化（重いので必要最小限）
    """
    try:
        values = ws.get_all_values()
        if not values:
            return pd.DataFrame()
        header = values[0]
        body = values[1:]
        if not body:
            return pd.DataFrame(columns=header)
        tail = body[-limit:]
        return pd.DataFrame(tail, columns=header)
    except Exception:
        return pd.DataFrame()


# -----------------------------
# UI
# -----------------------------
st.set_page_config(page_title=APP_TITLE, layout="wide")

st.title(APP_TITLE)

left, main = st.columns([1, 3], gap="large")

with left:
    st.subheader("設定 / 状態")

    # メニュー読み込み
    menu_df = _load_menu_csv(MENU_CSV_PATH)
    menu_opts = _menu_options(menu_df)

    st.caption("Sheets から読み書きします。エラーが出たら Secrets/共有権限 を確認。")

    # Sheets接続チェック
    gc, gc_err = _get_gspread_client()
    spreadsheet_id, worksheet_name, sheets_err = _get_sheet_params()

    if gc_err:
        st.error("Google Sheets 接続NG")
        st.code(gc_err)
        ws = None
    elif sheets_err:
        st.error("Google Sheets 接続NG")
        st.code(sheets_err)
        ws = None
    else:
        ws, ws_err = _open_or_create_worksheet(gc, spreadsheet_id, worksheet_name)
        if ws_err:
            st.error("Google Sheets 接続NG")
            st.code(ws_err)
        else:
            st.success("Google Sheets 接続OK")
            st.caption(f"Spreadsheet: {spreadsheet_id}")
            st.caption(f"Worksheet: {worksheet_name}")

            # headerを保証
            _ensure_header(
                ws,
                header=[
                    "timestamp_jst",
                    "date",
                    "time",
                    "menu",
                    "duration_min",
                    "intensity",
                    "memo",
                ],
            )

    st.divider()
    st.subheader("メニュー一覧（CSV）")
    st.caption(f"{len(menu_opts)} 件読み込み")
    if len(menu_opts) > 0:
        st.write(menu_opts[:30] if len(menu_opts) > 30 else menu_opts)
    else:
        st.warning("メニューCSVが空、または列が認識できません。")

with main:
    st.header("記録入力")

    now = _now_jst()
    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        date_val = st.date_input("日付", value=now.date())
        time_val = st.time_input("時間", value=now.time().replace(second=0, microsecond=0))

    with col2:
        duration_min = st.number_input("時間（分）", min_value=0, max_value=1000, value=60, step=5)
        intensity = st.selectbox("強度", ["軽め", "普通", "きつい", "限界"], index=1)

    with col3:
        if menu_opts:
            menu = st.selectbox("メニュー", menu_opts, index=0)
        else:
            menu = st.text_input("メニュー（手入力）", value="")

        memo = st.text_area("メモ（任意）", height=120, placeholder="例：フォーム意識、疲労感、痛み、天候など")

    st.divider()

    btn_col1, btn_col2 = st.columns([1, 2])
    with btn_col1:
        do_save = st.button("Sheetsに保存", type="primary", use_container_width=True)
    with btn_col2:
        st.caption("保存できない場合：①Secretsのprivate_key改行崩れ（Incorrect padding） ②共有権限不足（404） ③spreadsheet_id/worksheet_name違い を確認")

    if do_save:
        if ws is None:
            st.error("Sheetsに接続できていないので保存できません（左のエラーを確認）")
        else:
            timestamp_jst = _now_jst().strftime("%Y-%m-%d %H:%M:%S")
            row = [
                timestamp_jst,
                date_val.strftime("%Y-%m-%d"),
                time_val.strftime("%H:%M"),
                _safe_str(menu).strip(),
                str(int(duration_min)),
                _safe_str(intensity),
                _safe_str(memo).strip(),
            ]
            ok, msg = _append_log_row(ws, row)
            if ok:
                st.success("保存しました ✅")
            else:
                st.error("保存に失敗しました ❌")
                st.code(msg)
                st.info(
                    "【よくある原因】\n"
                    "- 404: スプレッドシートをサービスアカウントに共有してない / spreadsheet_id間違い\n"
                    "- Incorrect padding: Secrets内private_keyの改行崩れ\n"
                )

    st.subheader("最近の記録（Sheets）")
    if ws is None:
        st.info("Sheets接続がOKになったらここに表示されます。")
    else:
        recent_df = _read_recent(ws, limit=50)
        if recent_df.empty:
            st.info("まだ記録がありません。")
        else:
            st.dataframe(recent_df, use_container_width=True)
