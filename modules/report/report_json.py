# modules/report/report_json.py
from __future__ import annotations

from typing import Any, Dict

from .report_logic import ReportData


def reportdata_to_dict(rd: ReportData) -> Dict[str, Any]:
    # pandas をそのまま返さず、最低限JSON化しやすい形にする
    portfolio_rows = []
    if rd.portfolio is not None and not rd.portfolio.empty:
        # _dt はTimestampなので string 化
        df = rd.portfolio.copy()
        if "_dt" in df.columns:
            df["_dt"] = df["_dt"].astype(str)
        portfolio_rows = df.to_dict(orient="records")

    return {
        "meta": rd.meta,
        "months": rd.months,
        "roadmap_for_month": rd.roadmap_for_month,
        "portfolio": portfolio_rows,
    }
