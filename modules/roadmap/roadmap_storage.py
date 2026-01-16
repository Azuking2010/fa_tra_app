# modules/roadmap/roadmap_storage.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple, Optional

import pandas as pd
import re

import gspread
from google.oauth2.service_account import Credentials

from modules.roadmap.roadmap_schema import ROADMAP_COLUMNS, ROADMAP_NUMERIC_COLS, ROADMAP_BOOL_COLS


def _norm_ym(v: Any) -> str:
    """
    'YYYY-MM' に正規化
    許容: YYYY-M, YYYY/MM, YYYY.MM など
    """
    s = "" if v is None else str(v).strip()
    if not s:
        return ""
    s = s.replace("/", "-").replace(".", "-")
    m = re.match(r"^(\d{4})-(\d{1,2})$", s)
    if m:
        y = int(m.group(1))
        mm = int(m.group(2))
        return f"{y:04d}-{mm:02d}"
    # 余計な文字が付いてても先頭が YYYY-MM なら拾う
    m2 = re.match(r"^(\d{4})-(\d{2}).*$", s)
    if m2:
        y = int(m2.group(1))
        mm = int(m2.group(2))
        return f"{y:04d}-{mm:02d}"
    return s


def _to_bool(v: Any) -> Optional[bool]:
    if v is None:
        return None
    s = str(v).strip().lower()
    if s in ["true", "1", "yes", "y", "on"]:
        return True
    if s in ["false", "0", "no", "n", "off"]:
        return False
    if s == "":
        return None
    return None


@dataclass
class RoadmapSheetsStorage:
    st: Any
    spreadsheet_id: str
    roadmap_worksheet_name: str = "ROADMAP"
    _client: Optional[gspread.Client] = None

    def _get_client(self) -> gspread.Client:
        if self._client is not None:
            return self._client

        sa_info = self.st.secrets["gcp_service_account"]
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        self._client = gspread.authorize(creds)
        return self._client

    def _open_ws(self):
        client = self._get_client()
        sh = client.open_by_key(self.spreadsheet_id)
        return sh.worksheet(self.roadmap_worksheet_name)

    def healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._open_ws()
            values = ws.get_all_values()
            if not values:
                return False, "ROADMAP: シートは存在するが空です（ヘッダ行が必要）"
            header = values[0]
            if header != ROADMAP_COLUMNS:
                return False, f"ROADMAP: ヘッダ不一致（Sheets側の1行目を確認してください）"
            return True, "ROADMAP: Sheets 接続OK"
        except Exception as e:
            return False, f"ROADMAP: 接続エラー: {e}"

    def load_all(self) -> pd.DataFrame:
        try:
            ws = self._open_ws()
            values = ws.get_all_values()
            if not values or len(values) < 2:
                return pd.DataFrame(columns=ROADMAP_COLUMNS)

            header = values[0]
            data = values[1:]
            df = pd.DataFrame(data, columns=header)

            # 欠け列補完（壊さない）
            for c in ROADMAP_COLUMNS:
                if c not in df.columns:
                    df[c] = ""
            df = df[ROADMAP_COLUMNS]

            # ym 正規化
            df["start_ym"] = df["start_ym"].apply(_norm_ym)
            df["end_ym"] = df["end_ym"].apply(_norm_ym)

            # bool
            for c in ROADMAP_BOOL_COLS:
                if c in df.columns:
                    df[c] = df[c].apply(_to_bool)

            # numeric
            for c in ROADMAP_NUMERIC_COLS:
                if c in df.columns:
                    df[c] = pd.to_numeric(df[c], errors="coerce")

            return df
        except Exception:
            return pd.DataFrame(columns=ROADMAP_COLUMNS)

    def append_row(self, row: Dict[str, Any]) -> None:
        """
        1行追加（必要になったら使う）。
        ※ヘッダ整合が取れている前提。勝手にヘッダを書き換えない。
        """
        ws = self._open_ws()

        # 列順を固定して追記
        values = []
        for c in ROADMAP_COLUMNS:
            values.append(row.get(c, ""))

        ws.append_row(values, value_input_option="USER_ENTERED")


def build_roadmap_storage(st) -> RoadmapSheetsStorage:
    """
    既存 storage.py は触らない方針のため、
    ROADMAP はここで直接 Sheets に接続する。
    """
    spreadsheet_id = str(st.secrets.get("spreadsheet_id", "")).strip()
    roadmap_ws = str(st.secrets.get("roadmap_worksheet", "ROADMAP")).strip() or "ROADMAP"
    return RoadmapSheetsStorage(st=st, spreadsheet_id=spreadsheet_id, roadmap_worksheet_name=roadmap_ws)
