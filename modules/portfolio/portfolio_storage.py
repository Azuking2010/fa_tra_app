# modules/portfolio_storage.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Tuple

import pandas as pd

from modules.portfolio_utils import (
    PORTFOLIO_COLUMNS,
    build_bmi_formula,
    df_from_sheet_values,
    ensure_header_exact,
)


@dataclass
class PortfolioSheetsStorage:
    st: Any
    spreadsheet_id: str
    worksheet_name: str  # "portfolio"

    def _client(self):
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

    def healthcheck(self) -> Tuple[bool, str]:
        try:
            ws = self._ws()
            _ = ws.acell("A1").value
            ensure_header_exact(ws)
            return True, f"{self.worksheet_name} シートに接続OK"
        except Exception as e:
            return False, f"portfolio Sheets 接続NG: {e}"

    def load_all(self) -> pd.DataFrame:
        ws = self._ws()
        ensure_header_exact(ws)
        values = ws.get_all_values()
        return df_from_sheet_values(values)

    def append_row(self, row_dict: Dict[str, Any]) -> None:
        """
        空白はそのまま空で保存（＝B-1方針）。
        bmi は保存時に数式を入れる（身長・体重が空なら空が表示される）。
        """
        ws = self._ws()
        ensure_header_exact(ws)

        # 追加前の行数（ヘッダー含む）
        values_before = ws.get_all_values()
        next_row_index = len(values_before) + 1  # 1-based row number

        # シートに書く並びを固定
        row_values: List[Any] = []
        for col in PORTFOLIO_COLUMNS:
            if col == "bmi":
                row_values.append("")  # まず空でOK（後から数式を入れる）
            else:
                v = row_dict.get(col, "")
                row_values.append("" if v is None else v)

        ws.append_row(row_values, value_input_option="USER_ENTERED")

        # bmi 数式を D列に入れる（列順は固定なので bmi は4列目= D）
        # ただし、身長/体重が空ならIFで空になる
        bmi_formula = build_bmi_formula(next_row_index)
        ws.update_acell(f"D{next_row_index}", bmi_formula)
