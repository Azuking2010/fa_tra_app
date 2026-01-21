# modules/report/report_pdf.py
from __future__ import annotations

from typing import Any


def build_report_pdf_bytes(*args: Any, **kwargs: Any) -> bytes:
    """
    PDF生成（現時点では“importで落ちない”ことを優先）
    必要になったら reportlab を関数内 import で実装する。
    """
    raise NotImplementedError("PDF出力は未実装です（importエラー回避のためのスタブ）")
