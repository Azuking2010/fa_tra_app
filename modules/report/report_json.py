# modules/report/report_json.py
from __future__ import annotations

import json
from dataclasses import is_dataclass, asdict
from datetime import date, datetime
from typing import Any

# pandas/numpy は入っている前提（requirementsにもある）
try:
    import pandas as pd
except Exception:
    pd = None

try:
    import numpy as np
except Exception:
    np = None


def _to_jsonable(obj: Any) -> Any:
    """
    JSONにできない型を、できる型に変換する。
    - pandas: Timestamp / NaT / DataFrame / Series
    - numpy: int64/float64/bool_ など
    - datetime/date
    - dataclass
    - set/tuple など
    """
    # None
    if obj is None:
        return None

    # 基本型
    if isinstance(obj, (str, int, float, bool)):
        return obj

    # datetime / date
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()

    # dataclass
    if is_dataclass(obj):
        return _to_jsonable(asdict(obj))

    # dict
    if isinstance(obj, dict):
        return {str(k): _to_jsonable(v) for k, v in obj.items()}

    # list/tuple/set
    if isinstance(obj, (list, tuple, set)):
        return [_to_jsonable(v) for v in obj]

    # numpy scalars
    if np is not None:
        try:
            if isinstance(obj, (np.integer,)):
                return int(obj)
            if isinstance(obj, (np.floating,)):
                # NaN/inf は JSON 的に扱いづらいので None に落とす
                fv = float(obj)
                if fv != fv:  # NaN
                    return None
                if fv in (float("inf"), float("-inf")):
                    return None
                return fv
            if isinstance(obj, (np.bool_,)):
                return bool(obj)
        except Exception:
            pass

    # pandas types
    if pd is not None:
        try:
            # Timestamp
            if isinstance(obj, pd.Timestamp):
                # NaT もここに来ることがある
                if pd.isna(obj):
                    return None
                return obj.isoformat()

            # NaT/NA/NaN 判定
            try:
                if pd.isna(obj):
                    return None
            except Exception:
                pass

            # DataFrame -> list[dict]
            if isinstance(obj, pd.DataFrame):
                # Timestamp等も混ざるので再帰変換
                records = obj.to_dict(orient="records")
                return _to_jsonable(records)

            # Series -> list
            if isinstance(obj, pd.Series):
                return _to_jsonable(obj.tolist())
        except Exception:
            pass

    # それっぽいオブジェクト（ReportDataなど）: 属性辞書をたどる
    if hasattr(obj, "__dict__"):
        try:
            return _to_jsonable(vars(obj))
        except Exception:
            pass

    # 最後の砦：文字列化
    return str(obj)


def build_report_json_bytes(report: Any) -> bytes:
    """
    report（ReportData or dict）をAI向けJSONとして出力する。
    ここでは「JSON化可能な構造」に必ず落とす。
    """
    # report が dict でも dataclass でもOK
    payload = _to_jsonable(report)

    return json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
