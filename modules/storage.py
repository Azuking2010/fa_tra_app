from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd
import os
from datetime import datetime


# ======================
# 既存：トレーニング記録（log）
# ======================
RECORD_COLUMNS = ["date", "weekday", "day", "item", "part", "done", "weight"]

# ======================
# 追加：ポートフォリオ（portfolio）
# ======================
PORTFOLIO_COLUMNS = [
    "date",
    "category",
    "metric",
    "value_num",
    "value_text",
    "unit",
    "title",
    "tags",
    "visibility",
    "url",
    "memo",
    "created_at",
    "updated_at",
]


def _now_iso() -> str:
    # Sheets/CSV 両対応で扱いやすいよう ISO 文字列に統一
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class BaseStorage:
    # ---------- 既存 ----------
    def healthcheck(self) -> Tuple[bool, str]:
        raise NotImplementedError

    def get_info(self) -> Dict[str, str]:
        return {}

    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def load_all_records(self) -> pd.DataFrame:
        """集計用に全件読む（log）。"""
        raise NotImplementedError

    # ---------- 追加：portfolio ----------
    def append_portfolio(self, rows: List[Dict[str, Any]]) -> None:
        """portfolio シートに追記する。"""
        raise NotImplementedError

    def load_all_portfolio(self) -> pd.DataFrame:
        """portfolio を全件読む。"""
        raise NotImplementedError

    # ---------- 追加：Sheets本体が欲しいとき用（任意） ----------
    def get_spreadsheet(self):
        """SheetsStorage の場合だけ gspread spreadsheet を返す（CSVでは None）。"""
        return None


# ============================================================
# CSV Storage（fallback）
#   - 既存の data.csv はそのまま
#   - portfolio は portfolio.csv に分離（混ぜない）
# ============================================================
@dataclass
class CSVStorage(BaseStorage):
    path: str = "data.csv"
    portfolio_path: str = "portfolio.csv"

    def _ensure_log(self):
        if not os.path.exists(self.path):
            pd.DataFrame(columns=RECORD_COLUMNS).to_csv(
                self.path, index=False, encoding="utf-8-sig"
            )

    def _ensure_portfolio(self):
        if not os.path.exists(self.portfolio_path):
            pd.DataFrame(columns=PORTFOLIO_COLUMNS).to_csv(
                self.portfolio_path, index=False, encoding="utf-8-sig"
            )

    def healthcheck(self) -> Tuple[bool, str]:
        try:
            self._ensure_log()
            self._ensure_portfolio()
            return True, "ローカルCSV（fallback）"
        except Exception as e:
            return False, f"CSVエラー: {e}"

    # ---------- log ----------
    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        self._ensure_log()
        df = pd.read_csv(self.path, encoding="utf-8-sig")
        add = pd.DataFrame(rows)
        out = pd.concat([df, add], ignore_index=True)
        out.to_csv(self.path, index=False, encoding="utf-8-sig")

    def load_all_records(self) -> pd.DataFrame:
        self._ensure_log()
        try:
            return pd.read_csv(self.path, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(self.path, encoding="utf-8")

    # ---------- portfolio ----------
    def append_portfolio(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        self._ensure_portfolio()
        df = pd.read_csv(self.portfolio_path, encoding="utf-8-sig")
        add = pd.DataFrame(rows)

        # created_at / updated_at の自動補完（未指定なら）
        if "created_at" not in add.columns:
            add["created_at"] = _now_iso()
        else:
            add["created_at"] = add["created_at"].fillna("").replace("", _now_iso())

        if "updated_at" not in add.columns:
            add["updated_at"] = _now_iso()
        else:
            add["updated_at"] = add["updated_at"].fillna("").replace("", _now_iso())

        # 欠け列があっても列順を揃える
        for c in PORTFOLIO_COLUMNS:
            if c not in add.columns:
                add[c] = ""

        add = add[PORTFOLIO_COLUMNS]
        out = pd.concat([df, add], ignore_index=True)
        out.to_csv(self.portfolio_path, index=False, encoding="utf-8-sig")

    def load_all_portfolio(self) -> pd.DataFrame:
        self._ensure_portfolio()
        try:
            df = pd.read_csv(self.portfolio_path, encoding="utf-8-sig")
        except Exception:
            df = pd.read_csv(self.portfolio_path, encoding="utf-8")

        # 型寄せ（value_num）
        if "value_num" in df.columns:
            df["value_num"] = pd.to_numeric(df["value_num"], errors="coerce")
        return df


# ============================================================
# Sheets Storage
#   - log: worksheet_name（従来どおり、secrets["worksheet"] で指定）
#   - portfolio: portfolio_worksheet_name（追加、デフォ "portfolio"）
# ============================================================
@dataclass
class SheetsStorage(BaseStorage):
    st: Any
    spreadsheet_id: str
    worksheet_name: str
    portfolio_worksheet_name: str = "portfolio"

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

    def get_spreadsheet(self):
        gc = self._client()
        return gc.open_by_key(self.spreadsheet_id)

    def _ws(self, name: str):
        sh = self.get_spreadsheet()
        return sh.worksheet(name)

    def get_info(self) -> Dict[str, str]:
        return {
            "spreadsheet_id": self.spreadsheet_id,
            "worksheet": self.worksheet_name,
            "portfolio_worksheet": self.portfolio_worksheet_name,
        }

    def healthcheck(self) -> Tuple[bool, str]:
        try:
            # log シート疎通
            ws_log = self._ws(self.worksheet_name)
            _ = ws_log.acell("A1").value

            # portfolio シート疎通（存在しない場合はエラーになるので明示）
            ws_pf = self._ws(self.portfolio_worksheet_name)
            _ = ws_pf.acell("A1").value

            return True, "Google Sheets 接続 OK"
        except Exception as e:
            return False, f"Google Sheets 接続NG: {e}"

    # ---------- header ensure ----------
    def _ensure_header(self, ws, columns: List[str]):
        a1 = ws.acell("A1").value
        if not a1:
            ws.append_row(columns, value_input_option="USER_ENTERED")

    # ---------- log ----------
    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        ws = self._ws(self.worksheet_name)
        self._ensure_header(ws, RECORD_COLUMNS)

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
        ws = self._ws(self.worksheet_name)
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

    # ---------- portfolio ----------
    def append_portfolio(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        ws = self._ws(self.portfolio_worksheet_name)
        self._ensure_header(ws, PORTFOLIO_COLUMNS)

        values = []
        now = _now_iso()
        for r in rows:
            created_at = r.get("created_at") or now
            updated_at = r.get("updated_at") or now

            values.append([
                r.get("date", ""),
                r.get("category", ""),
                r.get("metric", ""),
                r.get("value_num", ""),
                r.get("value_text", ""),
                r.get("unit", ""),
                r.get("title", ""),
                r.get("tags", ""),
                r.get("visibility", "private"),
                r.get("url", ""),
                r.get("memo", ""),
                created_at,
                updated_at,
            ])

        ws.append_rows(values, value_input_option="USER_ENTERED")

    def load_all_portfolio(self) -> pd.DataFrame:
        ws = self._ws(self.portfolio_worksheet_name)
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)

        # 欠け列があっても落ちないように最低限補完
        for c in PORTFOLIO_COLUMNS:
            if c not in df.columns:
                df[c] = ""

        # 型寄せ
        df["value_num"] = pd.to_numeric(df["value_num"], errors="coerce")

        return df[PORTFOLIO_COLUMNS]


def build_storage(st) -> BaseStorage:
    """
    secrets が揃ってたら Sheets。
    無ければ CSV（ローカル動作用）にフォールバック。
    """
    try:
        if "gcp_service_account" in st.secrets and "spreadsheet_id" in st.secrets:
            spreadsheet_id = str(st.secrets["spreadsheet_id"]).strip()
            worksheet = str(st.secrets.get("worksheet", "log")).strip()
            portfolio_worksheet = str(st.secrets.get("portfolio_worksheet", "portfolio")).strip()

            if spreadsheet_id:
                return SheetsStorage(
                    st=st,
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=worksheet,
                    portfolio_worksheet_name=portfolio_worksheet,
                )
    except Exception:
        pass

    return CSVStorage(path="data.csv", portfolio_path="portfolio.csv")
