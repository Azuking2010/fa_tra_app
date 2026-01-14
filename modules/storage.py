# modules/storage.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
import pandas as pd
import os
import re


# =========================
# 既存：トレーニングログ（log シート）
# =========================
RECORD_COLUMNS = ["date", "weekday", "day", "item", "part", "done", "weight"]


# =========================
# 追加：ポートフォリオ（portfolio シート）
# ※「列決め打ち」固定スキーマ
# ======================
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

# ======================
# 追加：未来予想図（ROADMAP シート）
# ======================
ROADMAP_COLUMNS = [
    "start_ym",
    "end_ym",
    "metric",
    "low",
    "mid",
    "high",
    "note",
    "topic_text",
    "achieved",
]

ROADMAP_NUMERIC_COLS = ["low", "mid", "high"]

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
]


def _sort_portfolio_by_date(df: pd.DataFrame) -> pd.DataFrame:
    """
    date 昇順（古→新）に安定ソート。
    date の parse に失敗した行は末尾。
    """
    if df is None or df.empty or "date" not in df.columns:
        return df

    out = df.copy()

    # pandas の to_datetime で parse（無効は NaT）
    out["_date_parsed"] = pd.to_datetime(out["date"], errors="coerce")

    # mergesort は stable（同一キーの相対順序が保たれる）
    out = out.sort_values(
        by=["_date_parsed"],
        ascending=True,
        na_position="last",
        kind="mergesort",
    ).drop(columns=["_date_parsed"])

    # index は整えておく（見やすさ＆後続処理安定）
    out = out.reset_index(drop=True)
    return out


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
        return False

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        return False, "portfolio 未対応"

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        raise NotImplementedError

    def load_all_portfolio(self) -> pd.DataFrame:
        # 既定：空DF
        return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

    # ===== roadmap（未来予想図）=====
    def supports_roadmap(self) -> bool:
        return False

    def roadmap_healthcheck(self) -> Tuple[bool, str]:
        return False, "ROADMAP 未対応"

    def load_all_roadmap(self) -> pd.DataFrame:
        return pd.DataFrame(columns=ROADMAP_COLUMNS)


@dataclass
class CSVStorage(BaseStorage):
    path: str
    portfolio_path: str
    roadmap_path: str = "roadmap.csv"

    # ===== log =====
    def healthcheck(self) -> Tuple[bool, str]:
        if not os.path.exists(self.path):
            return False, f"CSVが見つかりません: {self.path}"
        return True, f"CSV OK: {self.path}"

    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        df_new = pd.DataFrame(rows)
        if os.path.exists(self.path):
            df_old = pd.read_csv(self.path)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new
        df.to_csv(self.path, index=False)

    def load_all_records(self) -> pd.DataFrame:
        if not os.path.exists(self.path):
            return pd.DataFrame(columns=RECORD_COLUMNS)
        try:
            df = pd.read_csv(self.path)
        except Exception:
            return pd.DataFrame(columns=RECORD_COLUMNS)
        # 欠けてる列があっても落ちないように補完
        for c in RECORD_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        return df[RECORD_COLUMNS]

    # ===== portfolio =====
    def supports_portfolio(self) -> bool:
        return os.path.exists(self.portfolio_path)

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        if not self.supports_portfolio():
            return False, f"portfolio CSVが見つかりません: {self.portfolio_path}"
        return True, f"portfolio CSV OK: {self.portfolio_path}"

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        df_new = pd.DataFrame([row])
        if os.path.exists(self.portfolio_path):
            df_old = pd.read_csv(self.portfolio_path)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new
        df.to_csv(self.portfolio_path, index=False)

    def load_all_portfolio(self) -> pd.DataFrame:
        if not self.supports_portfolio():
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)
        try:
            df = pd.read_csv(self.portfolio_path)
        except Exception:
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

        # 列が揃ってなければ揃える（足りない列は空で追加）
        for c in PORTFOLIO_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        df = df[PORTFOLIO_COLUMNS]

        # boolean
        if "tcenter" in df.columns:
            df["tcenter"] = (
                df["tcenter"].astype(str).str.lower().isin(["true", "1", "yes", "y", "on"])
            )

        # numeric
        for c in PORTFOLIO_NUMERIC_COLS:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        return df

    def supports_roadmap(self) -> bool:
        return os.path.exists(self.roadmap_path)

    def roadmap_healthcheck(self) -> Tuple[bool, str]:
        if not self.supports_roadmap():
            return False, f"ROADMAP CSVが見つかりません: {self.roadmap_path}"
        return True, f"ROADMAP CSV OK: {self.roadmap_path}"

    def load_all_roadmap(self) -> pd.DataFrame:
        if not self.supports_roadmap():
            return pd.DataFrame(columns=ROADMAP_COLUMNS)
        try:
            df = pd.read_csv(self.roadmap_path)
        except Exception:
            return pd.DataFrame(columns=ROADMAP_COLUMNS)

        for c in ROADMAP_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        df = df[ROADMAP_COLUMNS]

        for c in ROADMAP_NUMERIC_COLS:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        return df


class SheetsStorage(BaseStorage):
    st: Any
    spreadsheet_id: str
    worksheet_name: str
    portfolio_worksheet_name: str = "portfolio"
    roadmap_worksheet_name: str = "ROADMAP"

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

    def _ws_roadmap(self):
        gc = self._client()
        sh = gc.open_by_key(self.spreadsheet_id)
        try:
            return sh.worksheet(self.roadmap_worksheet_name)
        except Exception:
            return sh.add_worksheet(title=self.roadmap_worksheet_name, rows=2000, cols=30)

    def _ensure_roadmap_header(self, ws) -> None:
        values = ws.get_all_values()
        if not values:
            ws.append_row(ROADMAP_COLUMNS, value_input_option="USER_ENTERED")
            return
        header = values[0]
        if header == ROADMAP_COLUMNS:
            return
        return

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
            # A1が読めればOK
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

        # 既定の列順に合わせる
        values = []
        for r in rows:
            values.append([r.get(c, "") for c in RECORD_COLUMNS])

        ws.append_rows(values, value_input_option="USER_ENTERED")

    def load_all_records(self) -> pd.DataFrame:
        ws = self._ws()
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=RECORD_COLUMNS)

        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)

        # 欠けてる列があっても落ちないように補完
        for c in RECORD_COLUMNS:
            if c not in df.columns:
                df[c] = ""

        return df[RECORD_COLUMNS]

    # ===== portfolio =====
    def supports_portfolio(self) -> bool:
        try:
            ws = self._ws_portfolio()
            return ws is not None
        except Exception:
            return False

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._ws_portfolio()
            _ = ws.acell("A1").value
            return True, "portfolio シートに接続OK"
        except Exception as e:
            return False, f"portfolio 接続エラー: {e}"

    def _ensure_portfolio_header(self, ws) -> None:
        values = ws.get_all_values()
        if not values:
            ws.append_row(PORTFOLIO_COLUMNS, value_input_option="USER_ENTERED")
            return
        header = values[0]
        if header == PORTFOLIO_COLUMNS:
            return
        # 既存がある場合は「壊さない」ため、勝手に上書きはしない
        return

    def _safe_float(self, v: Any):
        try:
            if v is None:
                return None
            s = str(v).strip()
            if s == "":
                return None
            return float(s)
        except Exception:
            return None

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        """
        1行追加。
        空欄は空のまま。
        """
        ws = self._ws_portfolio()
        self._ensure_portfolio_header(ws)

        values = []
        for c in PORTFOLIO_COLUMNS:
            values.append(row.get(c, ""))

        ws.append_row(values, value_input_option="USER_ENTERED")

    def load_all_portfolio(self) -> pd.DataFrame:
        """
        ★重要：date 昇順（古→新）で返す
        これにより、UI/集計側で「末尾＝date的に最新」を意味するようになる。
        （同一dateの複数行は追記順を維持）
        """
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

        return _sort_portfolio_by_date(df)

    # ===== roadmap =====
    def supports_roadmap(self) -> bool:
        try:
            ws = self._ws_roadmap()
            return ws is not None
        except Exception:
            return False

    def roadmap_healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._ws_roadmap()
            self._ensure_roadmap_header(ws)
            values = ws.get_all_values()
            if not values:
                return True, "ROADMAP シートを作成しました（空）"
            header = values[0] if values else []
            if header != ROADMAP_COLUMNS:
                return False, f"ROADMAP ヘッダ不一致: {header} / expected: {ROADMAP_COLUMNS}"
            return True, "ROADMAP シートに接続OK"
        except Exception as e:
            return False, f"ROADMAP 接続エラー: {e}"

    def load_all_roadmap(self) -> pd.DataFrame:
        if not self.supports_roadmap():
            return pd.DataFrame(columns=ROADMAP_COLUMNS)

        ws = self._ws_roadmap()
        self._ensure_roadmap_header(ws)
        values = ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame(columns=ROADMAP_COLUMNS)

        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)

        for c in ROADMAP_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        df = df[ROADMAP_COLUMNS]

        for c in ROADMAP_NUMERIC_COLS:
            df[c] = pd.to_numeric(df[c], errors="coerce")

        def _norm_ym(v):
            s = str(v).strip()
            if not s:
                return ""
            s = s.replace("/", "-").replace(".", "-")
            m2 = re.match(r"^(\d{4})-(\d{1,2})$", s)
            if m2:
                return f"{int(m2.group(1)):04d}-{int(m2.group(2)):02d}"
            m3 = re.match(r"^(\d{4})-(\d{2}).*$", s)
            if m3:
                return f"{int(m3.group(1)):04d}-{int(m3.group(2)):02d}"
            return s

        df["start_ym"] = df["start_ym"].apply(_norm_ym)
        df["end_ym"] = df["end_ym"].apply(_norm_ym)
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
            portfolio_ws = str(st.secrets.get("portfolio_worksheet", "portfolio")).strip()
            roadmap_ws = str(st.secrets.get("roadmap_worksheet", "ROADMAP")).strip()

            if spreadsheet_id:
                return SheetsStorage(
                    st=st,
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=worksheet,
                    portfolio_worksheet_name=portfolio_ws or "portfolio",
                    roadmap_worksheet_name=roadmap_ws or "ROADMAP",
                )
    except Exception:
        pass

    return CSVStorage(path="data.csv", portfolio_path="portfolio.csv", roadmap_path="roadmap.csv")
