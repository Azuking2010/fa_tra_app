from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import os

RECORD_COLUMNS = ["date", "weekday", "day", "item", "part", "done", "weight"]

class BaseStorage:
    def healthcheck(self) -> Tuple[bool, str]:
        raise NotImplementedError

    def get_info(self) -> Dict[str, str]:
        return {}

    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def load_all_records(self) -> pd.DataFrame:
        """集計用に全件読む。"""
        raise NotImplementedError


@dataclass
class CSVStorage(BaseStorage):
    path: str = "data.csv"

    def _ensure(self):
        if not os.path.exists(self.path):
            pd.DataFrame(columns=RECORD_COLUMNS).to_csv(self.path, index=False, encoding="utf-8-sig")

    def healthcheck(self) -> Tuple[bool, str]:
        try:
            self._ensure()
            return True, "ローカルCSV（fallback）"
        except Exception as e:
            return False, f"CSVエラー: {e}"

    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        self._ensure()
        df = pd.read_csv(self.path, encoding="utf-8-sig")
        add = pd.DataFrame(rows)
        out = pd.concat([df, add], ignore_index=True)
        out.to_csv(self.path, index=False, encoding="utf-8-sig")

    def load_all_records(self) -> pd.DataFrame:
        self._ensure()
        try:
            return pd.read_csv(self.path, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(self.path, encoding="utf-8")


@dataclass
class SheetsStorage(BaseStorage):
    st: Any
    spreadsheet_id: str
    worksheet_name: str

    def _client(self):
        # 遅延 import（ローカル環境に gspread が無いケースの保険）
        import gspread
        from google.oauth2.service_account import Credentials

        sa_info = dict(self.st.secrets["gcp_service_account"])
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(sa_info, scopes=scopes)
        return gspread.authorize(creds)

    def _ws(self):
        gc = self._client()
        sh = gc.open_by_key(self.spreadsheet_id)
        return sh.worksheet(self.worksheet_name)

    def get_info(self) -> Dict[str, str]:
        return {"spreadsheet_id": self.spreadsheet_id, "worksheet": self.worksheet_name}

    def healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._ws()
            # 1セル読む（疎通）
            _ = ws.acell("A1").value
            return True, "Google Sheets 接続 OK"
        except Exception as e:
            return False, f"Google Sheets 接続NG: {e}"

    def _ensure_header(self, ws):
        # A1 が空ならヘッダを書く
        a1 = ws.acell("A1").value
        if not a1:
            ws.append_row(RECORD_COLUMNS, value_input_option="USER_ENTERED")

    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        ws = self._ws()
        self._ensure_header(ws)

        values = []
        for r in rows:
            values.append([
                r.get("date", ""),
                r.get("weekday", ""),
                r.get("day", ""),
                r.get("item", ""),
                r.get("part", ""),
                bool(r.get("done", False)),
                r.get("weight", ""),  # 空文字ならセルは空になる（nan表示回避）
            ])
        ws.append_rows(values, value_input_option="USER_ENTERED")

    def load_all_records(self) -> pd.DataFrame:
        ws = self._ws()
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=RECORD_COLUMNS)
        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)

        # 型寄せ
        if "done" in df.columns:
            df["done"] = df["done"].astype(str).str.lower().isin(["true", "1", "yes", "y"])
        if "weight" in df.columns:
            df["weight"] = pd.to_numeric(df["weight"], errors="coerce")

        return df


def build_storage(st) -> BaseStorage:
    """
    secrets が揃ってたら Sheets。
    無ければ CSV（ローカル動作用）にフォールバック。
    """
    try:
        if "gcp_service_account" in st.secrets and "spreadsheet_id" in st.secrets:
            spreadsheet_id = str(st.secrets["spreadsheet_id"]).strip()
            worksheet = str(st.secrets.get("worksheet", "log")).strip()
            if spreadsheet_id:
                return SheetsStorage(st=st, spreadsheet_id=spreadsheet_id, worksheet_name=worksheet)
    except Exception:
        pass

    return CSVStorage(path="data.csv")
