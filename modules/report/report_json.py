# modules/report/report_json.py
from __future__ import annotations

import json
from typing import Any, Dict

import numpy as np
import pandas as pd

from .report_logic import ReportData


def _to_jsonable(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, (np.floating, float)) and np.isnan(v):
        return None
    if isinstance(v, (np.integer, int)):
        return int(v)
    if isinstance(v, (np.floating, float)):
        return float(v)
    # Timestamp など
    try:
        if hasattr(v, "isoformat"):
            return v.isoformat()
    except Exception:
        pass
    return v


def build_report_json_dict(report: ReportData) -> Dict[str, Any]:
    df = report.portfolio.copy()

    # portfolio rows to dict（datetimeも文字列化）
    rows = []
    if not df.empty:
        for _, r in df.iterrows():
            item = {}
            for k, v in r.items():
                if k == "_dt":
                    item["dt"] = _to_jsonable(v)
                elif k.startswith("_"):
                    continue
                else:
                    item[k] = _to_jsonable(v)
            rows.append(item)

    out = {
        "meta": report.meta,
        "months": report.months,
        "roadmap_for_month": report.roadmap_for_month,
        "portfolio": rows,
    }
    return out


def build_report_json_bytes(report: ReportData) -> bytes:
    d = build_report_json_dict(report)
    return json.dumps(d, ensure_ascii=False, indent=2).encode("utf-8")
