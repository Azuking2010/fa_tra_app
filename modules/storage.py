# file: modules/storage.py
# purpose: Google Sheets / CSV fallback の保存・読み込み処理を管理する。
#          training log、portfolio、ROADMAP、IDP、Training Notice、Daily Schedule のデータアクセスを担当する。

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
# IDP schema
# =========================
IDP_PROFILE_COLUMNS = [
    "profile_id",
    "date",
    "grade",
    "school_year",
    "height_cm",
    "weight_kg",
    "main_position",
    "sub_position_1",
    "sub_position_2",
    "option_position",
    "dominant_foot",
    "team",
    "player_type",
    "note",
    "created_at",
    "updated_at",
]

IDP_GOALS_COLUMNS = [
    "goal_id",
    "category",
    "term",
    "goal_title",
    "goal_detail",
    "target_date",
    "priority",
    "status",
    "note",
    "created_at",
    "updated_at",
]

IDP_PLAYER_PROFILE_COLUMNS = [
    "profile_item_id",
    "category",
    "type",
    "item",
    "detail",
    "level",
    "priority",
    "status",
    "note",
    "created_at",
    "updated_at",
]

IDP_ACTION_PLAN_COLUMNS = [
    "action_id",
    "priority",
    "theme",
    "category",
    "issue",
    "action",
    "frequency",
    "related_training",
    "target_period",
    "status",
    "review_comment",
    "created_at",
    "updated_at",
]

IDP_REVIEW_COLUMNS = [
    "review_id",
    "review_month",
    "review_date",
    "related_goal_id",
    "related_action_id",
    "theme",
    "category",
    "priority",
    "execution_score",
    "awareness_score",
    "change_score",
    "overall_score",
    "continue_decision",
    "next_priority",
    "good_point",
    "issue",
    "next_action",
    "evidence_text",
    "parent_comment",
    "pep_comment",
    "created_at",
    "updated_at",
]

TRAINING_NOTICE_MASTER_COLUMNS = [
    "notice_id",
    "week_no",
    "day_of_week",
    "theme",
    "category",
    "title",
    "purpose",
    "menu_detail",
    "volume",
    "coaching_point",
    "line_message",
    "active",
    "created_at",
    "updated_at",
]

DAILY_SCHEDULE_COLUMNS = [
    "schedule_id",
    "date",
    "start_time",
    "end_time",
    "category",
    "title",
    "detail",
    "subject",
    "range_text",
    "goal",
    "done",
    "quality",
    "base_score",
    "quality_bonus",
    "total_score",
    "reason_if_not_done",
    "reflection",
    "memo",
    "created_at",
    "updated_at",
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

    def load_all_records(self) -> pd.DataFrame:
        return self.load_records()

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

    # ----- IDP -----
    def supports_idp(self) -> bool:
        return False

    def idp_healthcheck(self) -> Tuple[bool, str]:
        return False, "IDP: unsupported"

    def load_all_idp_profile(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_all_idp_goals(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_all_idp_player_profile(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_all_idp_action_plan(self) -> pd.DataFrame:
        raise NotImplementedError

    def load_all_idp_review(self) -> pd.DataFrame:
        raise NotImplementedError

    # ----- Training Notice -----
    def supports_training_notice(self) -> bool:
        return False

    def load_all_training_notice_master(self) -> pd.DataFrame:
        raise NotImplementedError

    # ----- Daily Schedule -----
    def supports_daily_schedule(self) -> bool:
        return False

    def load_all_daily_schedule(self) -> pd.DataFrame:
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

    idp_profile_worksheet_name: str = "IDP_Profile"
    idp_goals_worksheet_name: str = "IDP_Goals"
    idp_player_profile_worksheet_name: str = "IDP_PlayerProfile"
    idp_action_plan_worksheet_name: str = "IDP_ActionPlan"
    idp_review_worksheet_name: str = "IDP_Review"
    training_notice_master_worksheet_name: str = "Training_Notice_Master"
    daily_schedule_worksheet_name: str = "Daily_Schedule"

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

    def _load_sheet_as_df(self, worksheet_name: str, columns: List[str]) -> pd.DataFrame:
        ws = self._open_ws(worksheet_name)
        values = ws.get_all_values()
        if not values or len(values) < 2:
            return pd.DataFrame(columns=columns)

        header = values[0]
        rows = values[1:]
        df = pd.DataFrame(rows, columns=header)

        for c in columns:
            if c not in df.columns:
                df[c] = ""

        return df[columns]

    def _append_row_generic(self, worksheet_name: str, columns: List[str], row: Dict[str, Any]) -> None:
        ws = self._open_ws(worksheet_name)
        header = ws.row_values(1)
        if not header:
            ws.append_row(columns)
            header = columns

        cols = list(header)
        for k in row.keys():
            if k not in cols:
                cols.append(k)

        if cols != header:
            ws.update("A1", [cols])

        out = []
        for c in cols:
            out.append(row.get(c, ""))

        ws.append_row(out, value_input_option="USER_ENTERED")

    def get_info(self) -> Dict[str, Any]:
        return {
            "spreadsheet_id": self.spreadsheet_id,
            "worksheet": self.worksheet_name,
            "portfolio_worksheet": self.portfolio_worksheet_name,
            "roadmap_worksheet": self.roadmap_worksheet_name,
            "idp_profile_worksheet": self.idp_profile_worksheet_name,
            "idp_goals_worksheet": self.idp_goals_worksheet_name,
            "idp_player_profile_worksheet": self.idp_player_profile_worksheet_name,
            "idp_action_plan_worksheet": self.idp_action_plan_worksheet_name,
            "idp_review_worksheet": self.idp_review_worksheet_name,
            "training_notice_master_worksheet": self.training_notice_master_worksheet_name,
            "daily_schedule_worksheet": self.daily_schedule_worksheet_name,
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
        header = ws.row_values(1)
        if not header:
            ws.append_row(RECORD_COLUMNS)

        df = pd.DataFrame(rows)
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

    def load_all_records(self) -> pd.DataFrame:
        return self.load_records()

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
        self._append_row_generic(self.portfolio_worksheet_name, PORTFOLIO_COLUMNS, row)

    def load_all_portfolio(self) -> pd.DataFrame:
        df = self._load_sheet_as_df(self.portfolio_worksheet_name, PORTFOLIO_COLUMNS)

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
        df = self._load_sheet_as_df(self.roadmap_worksheet_name, ROADMAP_COLUMNS)

        for c in ["min_value", "max_value"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.reset_index(drop=True)

    def append_roadmap_row(self, row: Dict[str, Any]) -> None:
        self._append_row_generic(self.roadmap_worksheet_name, ROADMAP_COLUMNS, row)

    # ----- IDP -----
    def supports_idp(self) -> bool:
        return True

    def idp_healthcheck(self) -> Tuple[bool, str]:
        required = [
            self.idp_profile_worksheet_name,
            self.idp_goals_worksheet_name,
            self.idp_player_profile_worksheet_name,
            self.idp_action_plan_worksheet_name,
            self.idp_review_worksheet_name,
        ]

        ok_names = []
        ng_names = []

        for name in required:
            try:
                ws = self._open_ws(name)
                _ = ws.row_values(1)
                ok_names.append(name)
            except Exception:
                ng_names.append(name)

        if ng_names:
            return False, f"IDP Sheets 一部NG: {', '.join(ng_names)}"
        return True, f"IDP Sheets OK: {', '.join(ok_names)}"

    def load_all_idp_profile(self) -> pd.DataFrame:
        df = self._load_sheet_as_df(self.idp_profile_worksheet_name, IDP_PROFILE_COLUMNS)
        for c in ["height_cm", "weight_kg"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    def load_all_idp_goals(self) -> pd.DataFrame:
        return self._load_sheet_as_df(self.idp_goals_worksheet_name, IDP_GOALS_COLUMNS)

    def load_all_idp_player_profile(self) -> pd.DataFrame:
        return self._load_sheet_as_df(self.idp_player_profile_worksheet_name, IDP_PLAYER_PROFILE_COLUMNS)

    def load_all_idp_action_plan(self) -> pd.DataFrame:
        return self._load_sheet_as_df(self.idp_action_plan_worksheet_name, IDP_ACTION_PLAN_COLUMNS)

    def load_all_idp_review(self) -> pd.DataFrame:
        return self._load_sheet_as_df(self.idp_review_worksheet_name, IDP_REVIEW_COLUMNS)

    # ----- Training Notice -----
    def supports_training_notice(self) -> bool:
        return True

    def load_all_training_notice_master(self) -> pd.DataFrame:
        return self._load_sheet_as_df(self.training_notice_master_worksheet_name, TRAINING_NOTICE_MASTER_COLUMNS)

    # ----- Daily Schedule -----
    def supports_daily_schedule(self) -> bool:
        return True

    def load_all_daily_schedule(self) -> pd.DataFrame:
        df = self._load_sheet_as_df(self.daily_schedule_worksheet_name, DAILY_SCHEDULE_COLUMNS)

        for c in ["base_score", "quality_bonus", "total_score"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        return df


# =========================
# CSV storage (local fallback)
# =========================
@dataclass
class CSVStorage(BaseStorage):
    path: str
    portfolio_path: str
    roadmap_path: str = "roadmap.csv"

    idp_profile_path: str = "idp_profile.csv"
    idp_goals_path: str = "idp_goals.csv"
    idp_player_profile_path: str = "idp_player_profile.csv"
    idp_action_plan_path: str = "idp_action_plan.csv"
    idp_review_path: str = "idp_review.csv"
    training_notice_master_path: str = "training_notice_master.csv"
    daily_schedule_path: str = "daily_schedule.csv"

    def _load_csv_as_df(self, path: str, columns: List[str]) -> pd.DataFrame:
        if not os.path.exists(path):
            return pd.DataFrame(columns=columns)
        try:
            df = pd.read_csv(path)
        except Exception:
            return pd.DataFrame(columns=columns)

        for c in columns:
            if c not in df.columns:
                df[c] = ""

        return df[columns]

    def _append_csv_row(self, path: str, columns: List[str], row: Dict[str, Any]) -> None:
        df_new = pd.DataFrame([row])
        if os.path.exists(path):
            df_old = pd.read_csv(path)
            df = pd.concat([df_old, df_new], ignore_index=True)
        else:
            df = df_new

        for c in columns:
            if c not in df.columns:
                df[c] = ""

        df.to_csv(path, index=False)

    # ===== log =====
    def healthcheck(self) -> Tuple[bool, str]:
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

        for c in RECORD_COLUMNS:
            if c not in df.columns:
                df[c] = ""
        df = df[RECORD_COLUMNS]
        df.to_csv(self.path, index=False)

    def load_records(self) -> pd.DataFrame:
        return self._load_csv_as_df(self.path, RECORD_COLUMNS)

    def load_all_records(self) -> pd.DataFrame:
        return self.load_records()

    # ===== portfolio =====
    def supports_portfolio(self) -> bool:
        return True

    def portfolio_healthcheck(self) -> Tuple[bool, str]:
        if not os.path.exists(self.portfolio_path):
            return False, f"portfolio CSVが見つかりません: {self.portfolio_path}"
        return True, f"portfolio CSV OK: {self.portfolio_path}"

    def append_portfolio_row(self, row: Dict[str, Any]) -> None:
        self._append_csv_row(self.portfolio_path, PORTFOLIO_COLUMNS, row)

    def load_all_portfolio(self) -> pd.DataFrame:
        df = self._load_csv_as_df(self.portfolio_path, PORTFOLIO_COLUMNS)

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
        df = self._load_csv_as_df(self.roadmap_path, ROADMAP_COLUMNS)

        for c in ["min_value", "max_value"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        return df.reset_index(drop=True)

    def append_roadmap_row(self, row: Dict[str, Any]) -> None:
        self._append_csv_row(self.roadmap_path, ROADMAP_COLUMNS, row)

    # ===== IDP =====
    def supports_idp(self) -> bool:
        return True

    def idp_healthcheck(self) -> Tuple[bool, str]:
        return True, "IDP CSV fallback OK"

    def load_all_idp_profile(self) -> pd.DataFrame:
        df = self._load_csv_as_df(self.idp_profile_path, IDP_PROFILE_COLUMNS)
        for c in ["height_cm", "weight_kg"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df

    def load_all_idp_goals(self) -> pd.DataFrame:
        return self._load_csv_as_df(self.idp_goals_path, IDP_GOALS_COLUMNS)

    def load_all_idp_player_profile(self) -> pd.DataFrame:
        return self._load_csv_as_df(self.idp_player_profile_path, IDP_PLAYER_PROFILE_COLUMNS)

    def load_all_idp_action_plan(self) -> pd.DataFrame:
        return self._load_csv_as_df(self.idp_action_plan_path, IDP_ACTION_PLAN_COLUMNS)

    def load_all_idp_review(self) -> pd.DataFrame:
        return self._load_csv_as_df(self.idp_review_path, IDP_REVIEW_COLUMNS)

    # ===== Training Notice =====
    def supports_training_notice(self) -> bool:
        return True

    def load_all_training_notice_master(self) -> pd.DataFrame:
        return self._load_csv_as_df(self.training_notice_master_path, TRAINING_NOTICE_MASTER_COLUMNS)

    # ===== Daily Schedule =====
    def supports_daily_schedule(self) -> bool:
        return True

    def load_all_daily_schedule(self) -> pd.DataFrame:
        df = self._load_csv_as_df(self.daily_schedule_path, DAILY_SCHEDULE_COLUMNS)
        for c in ["base_score", "quality_bonus", "total_score"]:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")
        return df


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
        for p in ["log.csv", "data.csv", "train_log.csv", "records.csv"]:
            try:
                if os.path.exists(p):
                    return p
            except Exception:
                pass
        return "log.csv"

    try:
        if "gcp_service_account" in st.secrets:
            spreadsheet_id = _pick_spreadsheet_id()
            worksheet = str(st.secrets.get("worksheet", "log")).strip()
            portfolio_ws = str(st.secrets.get("portfolio_worksheet", "portfolio")).strip()
            roadmap_ws = str(st.secrets.get("roadmap_worksheet", "ROADMAP")).strip()

            idp_profile_ws = str(st.secrets.get("idp_profile_worksheet", "IDP_Profile")).strip()
            idp_goals_ws = str(st.secrets.get("idp_goals_worksheet", "IDP_Goals")).strip()
            idp_player_profile_ws = str(st.secrets.get("idp_player_profile_worksheet", "IDP_PlayerProfile")).strip()
            idp_action_plan_ws = str(st.secrets.get("idp_action_plan_worksheet", "IDP_ActionPlan")).strip()
            idp_review_ws = str(st.secrets.get("idp_review_worksheet", "IDP_Review")).strip()
            training_notice_master_ws = str(st.secrets.get("training_notice_master_worksheet", "Training_Notice_Master")).strip()
            daily_schedule_ws = str(st.secrets.get("daily_schedule_worksheet", "Daily_Schedule")).strip()

            if spreadsheet_id:
                return SheetsStorage(
                    st=st,
                    spreadsheet_id=spreadsheet_id,
                    worksheet_name=worksheet or "log",
                    portfolio_worksheet_name=portfolio_ws or "portfolio",
                    roadmap_worksheet_name=roadmap_ws or "ROADMAP",
                    idp_profile_worksheet_name=idp_profile_ws or "IDP_Profile",
                    idp_goals_worksheet_name=idp_goals_ws or "IDP_Goals",
                    idp_player_profile_worksheet_name=idp_player_profile_ws or "IDP_PlayerProfile",
                    idp_action_plan_worksheet_name=idp_action_plan_ws or "IDP_ActionPlan",
                    idp_review_worksheet_name=idp_review_ws or "IDP_Review",
                    training_notice_master_worksheet_name=training_notice_master_ws or "Training_Notice_Master",
                    daily_schedule_worksheet_name=daily_schedule_ws or "Daily_Schedule",
                )
    except Exception:
        pass

    return CSVStorage(path=_pick_csv_path(), portfolio_path="portfolio.csv", roadmap_path="roadmap.csv")