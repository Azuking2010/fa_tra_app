# modules/storage.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import os
import pandas as pd

# gspread / google auth
import gspread
from google.oauth2.service_account import Credentials

# =========================
# Log schema (training log)
# =========================
RECORD_COLUMNS = [
    "date",
    "weekday",
    "day",
    "item",
    "part",
    "done",
    "weight",
]

# =========================
# Portfolio schema
# =========================
PORTFOLIO_COLUMNS = [
    "date",
    "height_cm",
    "weight_kg",
    "run_100m_sec",      # UIでは50mだが互換維持のため列名はrun_100m_sec
    "run_1500m_sec",
    "run_3000m_sec",
    "track_meet",
    "rank",
    "deviation",
    "rating",
    "score_jp",
    "score_math",
    "score_en",
    "score_sci",
    "score_soc",
    "tcenter",
    "soccer_tournament",
    "match_result",
    "video_url",
    "video_note",
    "note",
]

# =========================
# Roadmap schema (future targets)
# =========================
ROADMAP_COLUMNS = [
    "start_ym",
    "end_ym",
    "item_key",
    "label",
    "min_value",
    "max_value",
    "note",
]


# =========================
# Base storage interface
# =========================
class BaseStorage:
    def healthcheck(self) -> Tuple[bool, str]:
        raise NotImplementedError

    def get_info(self) -> Dict[str, Any]:
        return {}

    # ----- training log -----
    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        raise NotImplementedError

    def load_records(self) -> pd.DataFrame:
        raise NotImplementedError

    # ----- portfolio -----
    def supports_portfolio(self) -> bool:
        return False

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        return False, "portfolio: unsupported"

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        raise NotImplementedError

    def load_all_portfolio(self) -> pd.DataFrame:
        raise NotImplementedError

    # ----- roadmap -----
    def supports_roadmap(self) -> bool:
        return False

    def roadmap_healthcheck(self) -> Tuple[bool, str]:
        return False, "roadmap: unsupported"

    def load_all_roadmap(self) -> pd.DataFrame:
        raise NotImplementedError

    def append_roadmap_row(self, row: Dict[str, Any]) -> None:
        raise NotImplementedError


# =========================
# Sheets storage
# =========================
@dataclass
class SheetsStorage(BaseStorage):
    st: Any
    spreadsheet_id: str
    worksheet_name: str = "log"
    portfolio_worksheet_name: str = "portfolio"
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

    def _open_ws(self, name: str):
        client = self._get_client()
        sh = client.open_by_key(self.spreadsheet_id)
        return sh.worksheet(name)

    def get_info(self) -> Dict[str, Any]:
        return {
            "spreadsheet_id": self.spreadsheet_id,
            "worksheet": self.worksheet_name,
            "portfolio_worksheet": self.portfolio_worksheet_name,
            "roadmap_worksheet": self.roadmap_worksheet_name,
        }

    # ----- health -----
    def healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._open_ws(self.worksheet_name)
            _ = ws.row_values(1)
            return True, f"Sheets OK: {self.worksheet_name}"
        except Exception as e:
            return False, f"Sheets NG: {e}"

    # ----- training log -----
    def append_records(self, rows: List[Dict[str, Any]]) -> None:
        if not rows:
            return
        ws = self._open_ws(self.worksheet_name)
        # ヘッダーが無い場合は作る
        header = ws.row_values(1)
        if not header:
            ws.append_row(RECORD_COLUMNS)

        df = pd.DataFrame(rows)
        # 欠け列補完
        for c in RECORD_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        df = df[RECORD_COLUMNS]

        values = df.values.tolist()
        ws.append_rows(values, value_input_option="USER_ENTERED")

    def load_records(self) -> pd.DataFrame:
        ws = self._open_ws(self.worksheet_name)
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=RECORD_COLUMNS)

        header = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=header)
        for c in RECORD_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        return df[RECORD_COLUMNS]

    # ----- portfolio -----
    def supports_portfolio(self) -> bool:
        return True

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._open_ws(self.portfolio_worksheet_name)
            _ = ws.row_values(1)
            return True, f"portfolio Sheets OK: {self.portfolio_worksheet_name}"
        except Exception as e:
            return False, f"portfolio Sheets NG: {e}"

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        ws = self._open_ws(self.portfolio_worksheet_name)
        header = ws.row_values(1)
        if not header:
            ws.append_row(PORTFOLIO_COLUMNS)
            header = PORTFOLIO_COLUMNS

        # 既存ヘッダー優先で並べる（未知列は末尾に追加）
        cols = list(header)
        for k in row.keys():
            if k not in cols:
                cols.append(k)
        if cols != header:
            # ヘッダー更新
            ws.update("A1", [cols])

        out = []
        for c in cols:
            v = row.get(c, "")
            out.append(v)
        ws.append_row(out, value_input_option="USER_ENTERED")

    def load_all_portfolio(self) -> pd.DataFrame:
        ws = self._open_ws(self.portfolio_worksheet_name)
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

        header = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=header)

        # 欠けてる列補完
        for c in PORTFOLIO_COLUMNS:
            if c not in df.columns:
                df[c] = ""

        # 数値っぽい列をできるだけ数値化（NaNでもOK）
        num_cols = [
            "height_cm", "weight_kg", "run_100m_sec", "run_1500m_sec", "run_3000m_sec",
            "rank", "deviation", "rating", "score_jp", "score_math", "score_en", "score_sci", "score_soc",
        ]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        return df

    # ----- roadmap -----
    def supports_roadmap(self) -> bool:
        return True

    def roadmap_healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._open_ws(self.roadmap_worksheet_name)
            _ = ws.row_values(1)
            return True, f"roadmap Sheets OK: {self.roadmap_worksheet_name}"
        except Exception as e:
            return False, f"roadmap Sheets NG: {e}"

    def load_all_roadmap(self) -> pd.DataFrame:
        ws = self._open_ws(self.roadmap_worksheet_name)
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=ROADMAP_COLUMNS)

        header = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=header)

        for c in ROADMAP_COLUMNS:
            if c not in df.columns:
                df[c] = ""

        # min/maxは数値化しておく（NaNでもOK）
        for c in ["min_value", "max_value"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        # index は整えておく（見やすさ＆後続処理安定）
        out = df.reset_index(drop=True)
        return out

    def append_roadmap_row(self, row: Dict[str, Any]) -> None:
        ws = self._open_ws(self.roadmap_worksheet_name)
        header = ws.row_values(1)
        if not header:
            ws.append_row(ROADMAP_COLUMNS)
            header = ROADMAP_COLUMNS

        # 既存ヘッダー優先で並べる（未知列は末尾に追加）
        cols = list(header)
        for k in row.keys():
            if k not in cols:
                cols.append(k)
        if cols != header:
            ws.update("A1", [cols])

        out = []
        for c in cols:
            v = row.get(c, "")
            out.append(v)
        ws.append_row(out, value_input_option="USER_ENTERED")


# =========================
# CSV storage (local fallback)
# =========================
@dataclass
class CSVStorage(BaseStorage):
    path: str
    portfolio_path: str
    roadmap_path: str = "roadmap.csv"

    # ===== log =====
    def healthcheck(self) -> Tuple[bool, str]:
        # CSVは「初回保存で作られる」運用が多いので、未作成はエラー扱いにしない（壊さない原則）
        if not os.path.exists(self.path):
            return True, f"CSV未作成: {self.path}（初回保存で自動作成されます）"
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

        # 欠けてる列があっても落ちないように補完
        for c in RECORD_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        df = df[RECORD_COLUMNS]
        df.to_csv(self.path, index=False)

    def load_records(self) -> pd.DataFrame:
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
        return True

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        if not os.path.exists(self.portfolio_path):
            return False, f"portfolio CSVが見つかりません: {self.portfolio_path}"
        return True, f"portfolio CSV OK: {self.portfolio_path}"

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        df_new = pd.DataFrame([row])
        if os.path.exists(self.portfolio_path):
            df_old = pd.read_csv(self.portfolio_path)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new

        # 欠け列補完
        for c in PORTFOLIO_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        df.to_csv(self.portfolio_path, index=False)

    def load_all_portfolio(self) -> pd.DataFrame:
        if not os.path.exists(self.portfolio_path):
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)
        try:
            df = pd.read_csv(self.portfolio_path)
        except Exception:
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

        for c in PORTFOLIO_COLUMNS:
            if c not in df.columns:
                df[c] = ""

        num_cols = [
            "height_cm", "weight_kg", "run_100m_sec", "run_1500m_sec", "run_3000m_sec",
            "rank", "deviation", "rating", "score_jp", "score_math", "score_en", "score_sci", "score_soc",
        ]
        for c in num_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        return df

    # ===== roadmap =====
    def supports_roadmap(self) -> bool:
        return True

    def roadmap_healthcheck(self) -> Tuple[bool, str]:
        if not os.path.exists(self.roadmap_path):
            return False, f"roadmap CSVが見つかりません: {self.roadmap_path}"
        return True, f"roadmap CSV OK: {self.roadmap_path}"

    def load_all_roadmap(self) -> pd.DataFrame:
        if not os.path.exists(self.roadmap_path):
            return pd.DataFrame(columns=ROADMAP_COLUMNS)
        try:
            df = pd.read_csv(self.roadmap_path)
        except Exception:
            return pd.DataFrame(columns=ROADMAP_COLUMNS)

        for c in ROADMAP_COLUMNS:
            if c not in df.columns:
                df[c] = ""

        for c in ["min_value", "max_value"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        out = df.reset_index(drop=True)
        return out

    def append_roadmap_row(self, row: Dict[str, Any]) -> None:
        df_new = pd.DataFrame([row])
        if os.path.exists(self.roadmap_path):
            df_old = pd.read_csv(self.roadmap_path)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new

        for c in ROADMAP_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        df.to_csv(self.roadmap_path, index=False)


# =========================
# Factory
# =========================
def build_storage(st) -> BaseStorage:
    """
    secrets が揃ってたら Sheets。
    無ければ CSV（ローカル動作用）にフォールバック。

    ✅ 壊さない原則（互換性）
    - spreadsheet_id のキー名揺れに対応（例: spreadsheet_id / spreadsheetId / sheet_id / gsheet_id など）
    - spreadsheet_id が取得できるなら Sheets を優先（CSVへ落とさない）
    - CSV fallback のログCSV名も固定せず、既存ファイルを優先
    """

    def _pick_spreadsheet_id() -> str:
        # 1) 代表的なキー名を順に探す（トップレベル）
        candidates = [
            "spreadsheet_id",
            "spreadsheetId",
            "sheet_id",
            "sheetId",
            "gsheet_id",
            "gsheetId",
            "SPREADSHEET_ID",
        ]
        for k in candidates:
            try:
                if k in st.secrets:
                    v = str(st.secrets.get(k, "")).strip()
                    if v:
                        return v
            except Exception:
                continue

        # 2) セクション配下に入れているケースも拾う（例: [app], [settings] など）
        section_candidates = ["app", "settings", "config"]
        for sec in section_candidates:
            try:
                obj = st.secrets.get(sec, None)
                if isinstance(obj, dict):
                    for k in candidates:
                        v = str(obj.get(k, "")).strip()
                        if v:
                            return v
            except Exception:
                continue

        return ""

    def _pick_csv_path() -> str:
        # 既存のログCSVがあればそれを優先（従来互換）
        for p in ["log.csv", "data.csv", "train_log.csv", "records.csv"]:
            try:
                if os.path.exists(p):
                    return p
            except Exception:
                pass
        # 無ければ従来互換寄りの名前で新規作成させる
        return "log.csv"

    try:
        # service account があるなら Sheets を最優先で試みる
        if "gcp_service_account" in st.secrets:
            spreadsheet_id = _pick_spreadsheet_id()
            worksheet = str(st.secrets.get("worksheet", "log")).strip()
            portfolio_ws = str(st.secrets.get("portfolio_worksheet", "portfolio")).strip()
            roadmap_ws = str(st.secrets.get("roadmap_worksheet", "ROADMAP")).strip()

            if spreadsheet_id:
                return SheetsStorage(
                    st=st,
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=worksheet or "log",
                    portfolio_worksheet_name=portfolio_ws or "portfolio",
                    roadmap_worksheet_name=roadmap_ws or "ROADMAP",
                )
    except Exception:
        # ここで落ちても CSV にフォールバックしてアプリは動かす（ただしファイル名は互換優先）
        pass

    return CSVStorage(path=_pick_csv_path(), portfolio_path="portfolio.csv", roadmap_path="roadmap.csv")
