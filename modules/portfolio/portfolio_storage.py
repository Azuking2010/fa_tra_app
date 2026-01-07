# portfolio_storage.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd


PORTFOLIO_SHEET_NAME = "portfolio"

# あなたの確定ヘッダ
PORTFOLIO_COLUMNS: List[str] = [
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


def _is_blank_like(v: Any) -> bool:
    """空欄扱いの判定（保存・前回値探索に共通で使う）"""
    if v is None:
        return True
    if isinstance(v, str):
        s = v.strip()
        return s == "" or s.lower() == "nan"
    # 0を空欄扱いにする（あなたの方針）
    if isinstance(v, (int, float)):
        return float(v) == 0.0
    return False


@dataclass
class PortfolioStorage:
    """
    Sheets接続の薄いラッパ。
    既存のSheets接続（gspreadやgoogle-api）に合わせて
    _get_worksheet() を差し替えて使ってください。
    """

    sheets_client: Any
    spreadsheet_id: str
    worksheet_name: str = PORTFOLIO_SHEET_NAME

    def _get_worksheet(self):
        # gspread想定（既存実装に合わせて調整してOK）
        sh = self.sheets_client.open_by_key(self.spreadsheet_id)
        return sh.worksheet(self.worksheet_name)

    def ensure_header(self) -> None:
        ws = self._get_worksheet()
        values = ws.get_all_values()
        if not values:
            ws.append_row(PORTFOLIO_COLUMNS)
            return
        header = values[0]
        if header != PORTFOLIO_COLUMNS:
            # 既存ヘッダが違う場合は安全のため例外
            raise ValueError(
                f"portfolio header mismatch.\n"
                f"expected={PORTFOLIO_COLUMNS}\n"
                f"actual={header}"
            )

    def read_df(self) -> pd.DataFrame:
        ws = self._get_worksheet()
        values = ws.get_all_values()
        if len(values) <= 1:
            return pd.DataFrame(columns=PORTFOLIO_COLUMNS)

        header = values[0]
        data = values[1:]
        df = pd.DataFrame(data, columns=header)

        # 数値列を数値化（失敗はNaN）
        numeric_cols = [
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
        for c in numeric_cols:
            if c in df.columns:
                df[c] = pd.to_numeric(df[c], errors="coerce")

        # bool列（tcenter）
        if "tcenter" in df.columns:
            # Sheets上のTRUE/FALSEや空を想定
            df["tcenter"] = df["tcenter"].astype(str).str.upper().map(
                {"TRUE": True, "FALSE": False}
            )

        return df

    def append_row(self, row: Dict[str, Any]) -> None:
        """rowは PORTFOLIO_COLUMNS をキーに持つ dict を想定"""
        ws = self._get_worksheet()

        out: List[Any] = []
        for col in PORTFOLIO_COLUMNS:
            v = row.get(col, "")
            # 0は空白扱い（あなたの仕様）
            if _is_blank_like(v):
                out.append("")
            else:
                out.append(v)
        ws.append_row(out, value_input_option="USER_ENTERED")

    def get_latest_values(self) -> Dict[str, Any]:
        """
        列ごとに「最新の“値”」を返す。
        “最新行”ではなく、下から見て最初に見つかった非空(≠0)。
        """
        df = self.read_df()
        if df.empty:
            return {}

        latest: Dict[str, Any] = {}
        # 下から探索（最新行から過去へ）
        for col in PORTFOLIO_COLUMNS:
            if col == "date":
                continue
            if col not in df.columns:
                continue

            series = df[col]
            # object列は str / 空が混じるので、そのまま判定
            for v in reversed(series.tolist()):
                if not _is_blank_like(v):
                    latest[col] = v
                    break

        return latest
