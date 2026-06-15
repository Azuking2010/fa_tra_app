# file: modules/common_constants.py
# purpose: IDP・Daily Schedule・共通UIで使う定数、選択肢、基準年度計算を管理する。
#          各画面に同じ候補を重複して書かないための共通設定ファイル。

from __future__ import annotations

from datetime import date


# =========================
# 基準情報
# =========================
BASE_SCHOOL_YEAR = 2026
BASE_GRADE_LABEL = "中学2年"

# 2026年度 = 中学2年 を基準にする
GRADE_BY_OFFSET = {
    -2: "小学6年",
    -1: "中学1年",
    0: "中学2年",
    1: "中学3年",
    2: "高校1年",
    3: "高校2年",
    4: "高校3年",
}


def calc_school_year(today: date | None = None) -> int:
    """
    4月基準で年度を計算する。
    例：
    2026/04/01〜2027/03/31 = 2026年度
    """
    if today is None:
        today = date.today()

    if today.month >= 4:
        return int(today.year)
    return int(today.year) - 1


def calc_grade_label(today: date | None = None) -> str:
    """
    2026年度 = 中学2年 を基準に、現在の学年を自動計算する。
    """
    school_year = calc_school_year(today)
    offset = school_year - BASE_SCHOOL_YEAR
    return GRADE_BY_OFFSET.get(offset, "未設定")


def calc_school_year_label(today: date | None = None) -> str:
    """
    年度ラベルを返す。
    例：2026年度
    """
    return f"{calc_school_year(today)}年度"


# =========================
# IDP_Profile 用
# =========================
GRADE_OPTIONS = [
    "小学6年",
    "中学1年",
    "中学2年",
    "中学3年",
    "高校1年",
    "高校2年",
    "高校3年",
]

DOMINANT_FOOT_OPTIONS = [
    "右",
    "左",
    "両",
]

DEFAULT_DOMINANT_FOOT = "右"

POSITION_OPTIONS = [
    "FW",
    "0TOP",
    "R-WING",
    "L-WING",
    "OFH",
    "DFH",
    "ISH",
    "RSH",
    "LSH",
    "RSB",
    "LSB",
    "CB",
    "GK",
]


# =========================
# IDP 共通
# =========================
IDP_CATEGORY_OPTIONS = [
    "technical",
    "physical",
    "tactical",
    "mental",
    "study",
    "english",
    "career",
    "life",
    "other",
]

IDP_CATEGORY_LABELS = {
    "technical": "テクニカル",
    "physical": "フィジカル",
    "tactical": "タクティカル",
    "mental": "メンタル",
    "study": "学力",
    "english": "英語",
    "career": "進路",
    "life": "生活",
    "other": "その他",
}

IDP_STATUS_OPTIONS = [
    "active",
    "paused",
    "done",
    "review",
    "archived",
]

IDP_STATUS_LABELS = {
    "active": "実行中",
    "paused": "一時停止",
    "done": "完了",
    "review": "見直し中",
    "archived": "過去扱い",
}

IDP_PRIORITY_OPTIONS = [
    "1",
    "2",
    "3",
    "4",
    "5",
]

IDP_THEME_OPTIONS = [
    "オフザボール",
    "ネガティブトランジション",
    "55kg到達",
    "推進力向上",
    "左足強化",
    "学力維持",
    "英語強化",
    "進路準備",
    "その他",
]


# =========================
# IDP_Review 用
# =========================
REVIEW_SCORE_OPTIONS = [
    "◎",
    "○",
    "△",
    "×",
]

REVIEW_SCORE_LABELS = {
    "◎": "かなり良い",
    "○": "順調",
    "△": "少し改善",
    "×": "見直し必要",
}

CONTINUE_DECISION_OPTIONS = [
    "続ける",
    "少し変える",
    "一旦終了",
    "優先度を上げる",
    "優先度を下げる",
    "保留",
]


# =========================
# Daily Schedule 用
# =========================
SCHEDULE_CATEGORY_OPTIONS = [
    "睡眠",
    "食事",
    "準備",
    "移動",
    "学校",
    "練習",
    "試合",
    "自主練",
    "勉強",
    "英語",
    "休憩",
    "自由時間",
    "風呂",
    "生活",
    "その他",
]

SUBJECT_OPTIONS = [
    "国語",
    "数学",
    "英語",
    "理科",
    "社会",
    "保健体育",
    "技術家庭",
    "音楽",
    "美術",
    "提出物",
    "なし",
]

DONE_OPTIONS = [
    "Y",
    "N",
]

QUALITY_OPTIONS = [
    "◎",
    "○",
    "△",
    "×",
]

REASON_IF_NOT_DONE_OPTIONS = [
    "寝坊",
    "疲労",
    "体調不良",
    "時間不足",
    "予定変更",
    "忘れた",
    "やる気が出なかった",
    "天候",
    "家の都合",
    "学校課題",
    "その他",
]