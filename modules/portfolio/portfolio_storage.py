from __future__ import annotations

from datetime import datetime
from typing import List, Tuple, Optional

import pandas as pd


PORTFOLIO_SHEET_NAME = "portfolio"
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


class PortfolioStorage:
    """
    既存 storage を“土台”にして、同じ Spreadsheet 内の portfolio シートを操作する。
    - Sheets接続（secretsあり）のときだけ動かす
    - CSV fallback 時は誤更新防止のため停止（必要なら後でCSV版を作る）
    """

    def __init__(self, base_storage):
        self.base = base_storage

    def is_sheets_mode(self) -> bool:
        info = self.base.get_info() or {}
        # spreadsheet_id があれば Sheets と判断
        return "spreadsheet_id" in info

    def _get_sheet(self):
        """
        base_storage が内部で gspread を使っている前提で、
        - base_storage に gspread client を返す関数が無い場合でも、
          base_storage 側の実装に依存しないように “最低限の口” を用意している想定。
        もしここで落ちる場合は、base_storage の中身に合わせて調整する。
        """
        # ✅ まず、base_storage に “get_spreadsheet()” がある想定（無ければ後で合わせる）
        if not hasattr(self.base, "get_spreadsheet"):
            raise RuntimeError("storage に get_spreadsheet() がありません。modules/storage.py 側に追加が必要です。")

        ss = self.base.get_spreadsheet()
        try:
            ws = ss.worksheet(PORTFOLIO_SHEET_NAME)
        except Exception:
            ws = ss.add_worksheet(title=PORTFOLIO_SHEET_NAME, rows=2000, cols=len(PORTFOLIO_COLUMNS))
            ws.append_row(PORTFOLIO_COLUMNS)
        return ws

    def ensure_header(self) -> Tuple[bool, str]:
        if not self.is_sheets_mode():
            return False, "Sheets接続ではないため portfolio は無効（CSV fallback）"

        ws = self._get_sheet()
        header = ws.row_values(1)
        if header != PORTFOLIO_COLUMNS:
            # ヘッダが違う場合は安全のため止める（自動修正は事故りやすい）
            return False, f"portfolio シートのヘッダが想定と違います。1行目を {PORTFOLIO_COLUMNS} にしてください。"
        return True, "portfolio シートOK"

    def append_rows(self, rows: List[dict]) -> None:
        ok, msg = self.ensure_header()
        if not ok:
            raise RuntimeError(msg)

        ws = self._get_sheet()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        out = []
        for r in rows:
            rr = dict(r)
            rr["created_at"] = rr.get("created_at") or now
            rr["updated_at"] = rr.get("updated_at") or now
            out.append([rr.get(c, "") for c in PORTFOLIO_COLUMNS])

        # まとめて追記
        ws.append_rows(out, value_input_option="USER_ENTERED")

    def load_df(self) -> pd.DataFrame:
        ok, msg = self.ensure_header()
        if not ok:
            raise RuntimeError(msg)

        ws = self._get_sheet()
        values = ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)

        # 型寄せ
        if "value_num" in df.columns:
            df["value_num"] = pd.to_numeric(df["value_num"], errors="coerce")

        return df
