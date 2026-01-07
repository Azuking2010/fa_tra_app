from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import pandas as pd
import os


# =========================
# 既存：トレーニングログ（log シート）
# =========================
RECORD_COLUMNS = ["date", "weekday", "day", "item", "part", "done", "weight"]


# =========================
# 追加：ポートフォリオ（portfolio シート）
# ※「列決め打ち」固定スキーマ
# =========================
PORTFOLIO_COLUMNS = [
    "date",
    "height_cm",
    "weight_kg",
    "bmi",
    "run_100m_sec",
    "run_1500m_sec",
    "run_3000m_sec",
    "track_meet",
    "rank",
    "deviation",
    "score_jp",
    "score_math",
    "score_en",
    "score_sci",
    "score_soc",
    "rating",
    "tcenter",
    "soccer_tournament",
    "match_result",
    "video_url",
    "video_note",
    "note",
]

# 数値として扱いたい列（portfolio）
PORTFOLIO_NUMERIC_COLS = [
    "height_cm",
    "weight_kg",
    "bmi",
    "run_100m_sec",
    "run_1500m_sec",
    "run_3000m_sec",
    "rank",
    "deviation",
    "score_jp",
    "score_math",
    "score_en",
    "score_sci",
    "score_soc",
    "rating",
]


class BaseStorage:
    # ===== log =====
    def healthcheck(self) -> Tuple[bool, str]:
        raise NotImplementedError

    def get_info(self) -> Dict[str, str]:
        return {}

    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def load_all_records(self) -> pd.DataFrame:
        """集計用に全件読む（log）。"""
        raise NotImplementedError

    # ===== portfolio（列決め打ち）=====
    def supports_portfolio(self) -> bool:
        """portfolio を使えるストレージか（基本は Sheets 時のみ True でOK）。"""
        return False

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        return False, "portfolio 未対応"

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        raise NotImplementedError

    def load_all_portfolio(self) -> pd.DataFrame:
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)


@dataclass
class CSVStorage(BaseStorage):
    path: str = "data.csv"
    portfolio_path: str = "portfolio.csv"

    def _ensure(self):
        if not os.path.exists(self.path):
            pd.DataFrame(columns=RECORD_COLUMNS).to_csv(self.path, index=False, encoding="utf-8-sig")

    def _ensure_portfolio(self):
        if not os.path.exists(self.portfolio_path):
            pd.DataFrame(columns=PORTFOLIO_COLUMNS).to_csv(self.portfolio_path, index=False, encoding="utf-8-sig")

    # ===== log =====
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

    # ===== portfolio =====
    def supports_portfolio(self) -> bool:
        # いまは安全のため、CSV fallback では portfolio を無効にする方針を維持
        return False

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        return False, "Sheets接続ではないため portfolio は無効（CSV fallback）"

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        # CSV では無効（誤運用防止）
        return

    def load_all_portfolio(self) -> pd.DataFrame:
        self._ensure_portfolio()
        try:
            return pd.read_csv(self.portfolio_path, encoding="utf-8-sig")
        except Exception:
            return pd.read_csv(self.portfolio_path, encoding="utf-8")


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

    def _ws(self):
        gc = self._client()
        sh = gc.open_by_key(self.spreadsheet_id)
        return sh.worksheet(self.worksheet_name)

    def _ws_portfolio(self):
        gc = self._client()
        sh = gc.open_by_key(self.spreadsheet_id)
        return sh.worksheet(self.portfolio_worksheet_name)

    def get_info(self) -> Dict[str, str]:
        return {
            "spreadsheet_id": self.spreadsheet_id,
            "worksheet": self.worksheet_name,
            "portfolio_worksheet": self.portfolio_worksheet_name,
        }

    # ===== log =====
    def healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._ws()
            _ = ws.acell("A1").value
            return True, "Google Sheets 接続 OK"
        except Exception as e:
            return False, f"Google Sheets 接続NG: {e}"

    def _ensure_header(self, ws):
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
            values.append(
                [
                    r.get("date", ""),
                    r.get("weekday", ""),
                    r.get("day", ""),
                    r.get("item", ""),
                    r.get("part", ""),
                    bool(r.get("done", False)),
                    r.get("weight", ""),
                ]
            )
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

    # ===== portfolio =====
    def supports_portfolio(self) -> bool:
        return True

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._ws_portfolio()
            _ = ws.acell("A1").value
            return True, "portfolio シートに接続OK"
        except Exception as e:
            return False, f"portfolio 接続NG: {e}"

    def _ensure_portfolio_header(self, ws):
        """
        A1 が空ならヘッダを書き込み。
        既にヘッダがある場合は「一致してるか」を軽くチェックして、
        おかしければ警告（自動修復はしない：事故防止）。
        """
        a1 = ws.acell("A1").value
        if not a1:
            ws.append_row(PORTFOLIO_COLUMNS, value_input_option="USER_ENTERED")
            return

        # 既存ヘッダの整合チェック（安全のため警告のみ）
        try:
            header = ws.row_values(1)
            # row_values は末尾の空セルを省略することがあるので、先頭一致で見る
            if header[: len(PORTFOLIO_COLUMNS)] != PORTFOLIO_COLUMNS:
                # Streamlit に警告を出す（storage内だが st を持っているので可能）
                self.st.warning(
                    "portfolio シートのヘッダが想定と一致しません。"
                    "（列ズレの可能性）シート1行目を PORTFOLIO_COLUMNS に合わせてください。"
                )
        except Exception:
            # チェックできなくても動作は継続
            pass

    def _safe_cell_value(self, v: Any):
        """gspread に渡す値の安全化（None/NaNなどを空に）"""
        if v is None:
            return ""
        # pandas / numpy の NaN 対策
        try:
            if pd.isna(v):
                return ""
        except Exception:
            pass
        return v

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        """
        1行追加。
        空欄は空のまま（B-1）。
        bmi は Sheets 側の数式運用でもOKなので、基本は空で書く（rowに入ってれば書く）。
        """
        ws = self._ws_portfolio()
        self._ensure_portfolio_header(ws)

        values = []
        for c in PORTFOLIO_COLUMNS:
            v = self._safe_cell_value(row.get(c, ""))
            values.append(v)

        ws.append_row(values, value_input_option="USER_ENTERED")

    def load_all_portfolio(self) -> pd.DataFrame:
        ws = self._ws_portfolio()
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)

        # 欠けてる列があっても落ちないように補完
        for c in PORTFOLIO_COLUMNS:
            if c not in df.columns:
                df[c] = ""

        # boolean
        if "tcenter" in df.columns:
            df["tcenter"] = df["tcenter"].astype(str).str.lower().isin(["true", "1", "yes", "y", "on"])

        # numeric
        for c in PORTFOLIO_NUMERIC_COLS:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

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
            portfolio_ws = str(st.secrets.get("portfolio_worksheet", "portfolio")).strip()

            if spreadsheet_id:
                return SheetsStorage(
                    st=st,
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=worksheet,
                    portfolio_worksheet_name=portfolio_ws or "portfolio",
                )
    except Exception:
        pass

    return CSVStorage(path="data.csv", portfolio_path="portfolio.csv")
