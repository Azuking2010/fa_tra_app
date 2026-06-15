# file: modules/ui_components.py
# purpose: アプリ全体で共通利用する表示部品・入力補助関数を管理する。
#          各UIファイルで同じ見た目や入力ルールを重複実装しないための共通UI部品。

from __future__ import annotations

from typing import Any, Iterable, Optional

import pandas as pd


def is_blank_like(value: Any) -> bool:
    """
    空欄・None・NaN・文字列nan等を空扱いする。
    """
    if value is None:
        return True

    try:
        if pd.isna(value):
            return True
    except Exception:
        pass

    if isinstance(value, str):
        s = value.strip()
        if s == "":
            return True
        if s.lower() in ["nan", "none", "null"]:
            return True

    return False


def safe_text(value: Any, fallback: str = "—") -> str:
    """
    UI表示用に空欄を見やすくする。
    """
    if is_blank_like(value):
        return fallback
    return str(value)


def section_title(st, title: str, caption: Optional[str] = None) -> None:
    """
    セクションタイトルを統一表示する。
    """
    st.markdown(f"## {title}")
    if caption:
        st.caption(caption)


def small_note(st, text: str) -> None:
    """
    補足メモを統一表示する。
    """
    st.caption(text)


def display_dataframe(
    st,
    df: pd.DataFrame,
    *,
    empty_message: str = "データがありません。",
    height: int = 260,
    use_container_width: bool = True,
) -> None:
    """
    DataFrameを安全に表示する。
    """
    if df is None or df.empty:
        st.info(empty_message)
        return

    st.dataframe(df, use_container_width=use_container_width, height=height)


def latest_row(df: pd.DataFrame, date_col: str = "date") -> dict:
    """
    date列がある場合は日付順で最新行を返す。
    date列がなければ最後の行を返す。
    """
    if df is None or df.empty:
        return {}

    d = df.copy()

    if date_col in d.columns:
        try:
            d["_dt"] = pd.to_datetime(d[date_col], errors="coerce")
            d = d.sort_values(by=["_dt"], ascending=True, na_position="last")
        except Exception:
            pass

    row = d.iloc[-1].to_dict()
    row.pop("_dt", None)
    return row


def score_badge(score: Any) -> str:
    """
    ◎○△×を説明付きで表示する。
    """
    if is_blank_like(score):
        return "—"

    s = str(score).strip()
    mapping = {
        "◎": "◎ かなり良い",
        "○": "○ 順調",
        "△": "△ 少し改善",
        "×": "× 見直し必要",
    }
    return mapping.get(s, s)


def join_non_empty(values: Iterable[Any], separator: str = " / ") -> str:
    """
    空でない値だけをつないで表示する。
    """
    out = []
    for v in values:
        if not is_blank_like(v):
            out.append(str(v))
    if not out:
        return "—"
    return separator.join(out)