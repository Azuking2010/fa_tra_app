from dataclasses import dataclass
from datetime import date as date_type
from typing import Optional


PORTFOLIO_CATEGORIES = [
    "track",
    "body",
    "soccer",
    "study",
    "memo",
    "video",
]

VISIBILITY_VALUES = ["private", "share"]


@dataclass
class PortfolioRow:
    date: date_type
    category: str
    metric: str

    value_num: Optional[float] = None
    value_text: str = ""
    unit: str = ""
    title: str = ""
    tags: str = ""
    visibility: str = "private"
    url: str = ""
    memo: str = ""

    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict:
        """Sheets/CSV へ書き込む用（すべて文字列に寄せてもOKな形）"""
        return {
            "date": self.date.strftime("%Y-%m-%d"),
            "category": self.category,
            "metric": self.metric,
            "value_num": "" if self.value_num is None else self.value_num,
            "value_text": self.value_text,
            "unit": self.unit,
            "title": self.title,
            "tags": self.tags,
            "visibility": self.visibility,
            "url": self.url,
            "memo": self.memo,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
