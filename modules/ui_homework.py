# file: modules/ui_homework.py
# purpose: 夏休み課題の進捗登録、全体・教科別進捗、残り学習可能日数、
#          余裕度判定、Teacher Mikel Artetaへの導線を表示する。
#          Streamlitのmetric/progress部品は使わず、HTML/CSSで安定表示する。
#          page / sheet型の進捗から、予定ラインへ戻すための具体的な数量目安を自動計算する。

from __future__ import annotations

from datetime import date, datetime, timedelta
from html import escape
from typing import Dict, Iterable, List, Optional, Set, Tuple
import math
import uuid

import pandas as pd


DEFAULT_PLAN_START = date(2026, 7, 19)
DEFAULT_PLAN_END = date(2026, 8, 25)

# 2026年夏のサッカー遠征。宿題計画上の学習可能日から除外する。
NON_STUDY_START = date(2026, 7, 29)
NON_STUDY_END = date(2026, 8, 6)

DEFAULT_STUDY_COACH_URL = (
    "https://chatgpt.com/g/g-6a6426bc5fcc8191bd8a068bc748b41c-"
    "teacher-mikel-arteta"
)

SUBJECT_ORDER = ["国語", "数学", "英語", "理科", "社会"]

UNIT_LABELS = {
    "page": "ページ",
    "sheet": "枚・ページ",
    "step": "ステップ",
    "point": "ポイント",
    "percent": "%",
}

STATUS_MESSAGES = {
    "rainbow": ("🌈", "かなり余裕あり！この調子！"),
    "sun": ("☀️", "順調！いいペース！"),
    "partly": ("🌤️", "予定どおり！今日も少し進めよう"),
    "rain": ("☔️", "少し遅れてる！今日はペースアップ"),
    "thunder": (
        "⚡️",
        "ヤバい❗️マジでヤバい‼️\n"
        "このペースのままだと、サッカー禁止になるぞ💦\n"
        "Switchも禁止になるぞ🈲\n"
        "今日は絶対に進めよう。",
    ),
}


def _safe_float(value, default: float = 0.0) -> float:
    try:
        if value is None or str(value).strip() == "":
            return default
        number = float(value)
        if math.isnan(number):
            return default
        return number
    except Exception:
        return default


def _safe_int(value, default: int = 0) -> int:
    try:
        return int(round(_safe_float(value, float(default))))
    except Exception:
        return default


def _parse_date(value, fallback: date) -> date:
    try:
        parsed = pd.to_datetime(value, errors="coerce")
        if pd.isna(parsed):
            return fallback
        return parsed.date()
    except Exception:
        return fallback


def _settings_dict(df: pd.DataFrame) -> Dict[str, str]:
    if df is None or df.empty:
        return {}
    if "setting_key" not in df.columns or "setting_value" not in df.columns:
        return {}

    result: Dict[str, str] = {}
    for _, row in df.iterrows():
        key = str(row.get("setting_key", "")).strip()
        value = str(row.get("setting_value", "")).strip()
        if key:
            result[key] = value
    return result


def _date_range(start: date, end: date) -> Iterable[date]:
    if end < start:
        return []
    return (start + timedelta(days=i) for i in range((end - start).days + 1))


def _is_non_study_day(day: date) -> bool:
    return NON_STUDY_START <= day <= NON_STUDY_END


def _available_days(start: date, end: date) -> List[date]:
    return [day for day in _date_range(start, end) if not _is_non_study_day(day)]


def _schedule_metrics(
    today: date,
    plan_start: date,
    plan_end: date,
) -> Tuple[int, int, float]:
    available = _available_days(plan_start, plan_end)
    total_days = len(available)

    if total_days == 0:
        return 0, 0, 0.0

    elapsed_days = sum(1 for day in available if day <= today)
    remaining_days = sum(1 for day in available if day >= today)

    if today < plan_start:
        planned_progress = 0.0
        remaining_days = total_days
    elif today > plan_end:
        planned_progress = 100.0
        remaining_days = 0
    else:
        planned_progress = elapsed_days / total_days * 100.0

    return total_days, remaining_days, planned_progress


def _normalize_homework(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    work = df.copy()

    for column in [
        "start_value",
        "end_value",
        "total_units",
        "weight_per_unit",
        "sort_order",
    ]:
        if column in work.columns:
            work[column] = pd.to_numeric(work[column], errors="coerce")

    if "status" in work.columns:
        status = work["status"].astype(str).str.strip().str.lower()
        work = work[(status == "") | (status == "active")].copy()

    if "sort_order" in work.columns:
        work = work.sort_values(
            ["sort_order", "subject", "task_name"],
            na_position="last",
        )
    else:
        work = work.sort_values(["subject", "task_name"])

    return work.reset_index(drop=True)


def _normalize_progress(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame()

    progress = df.copy()
    for column in ["completed_start", "completed_end", "completed_value"]:
        if column in progress.columns:
            progress[column] = pd.to_numeric(progress[column], errors="coerce")
    return progress


def _task_universe(row: pd.Series) -> Set[int]:
    start_value = _safe_int(row.get("start_value"), 1)
    end_value = _safe_int(row.get("end_value"), 0)
    total_units = max(_safe_int(row.get("total_units"), 0), 0)

    if end_value >= start_value:
        universe = set(range(start_value, end_value + 1))
        if total_units > 0 and len(universe) > total_units:
            universe = set(sorted(universe)[:total_units])
        return universe

    if total_units > 0:
        return set(range(1, total_units + 1))

    return set()


def _completed_units_for_task(
    task_row: pd.Series,
    progress_df: pd.DataFrame,
) -> Set[int]:
    homework_id = str(task_row.get("homework_id", "")).strip()
    universe = _task_universe(task_row)

    if not homework_id or progress_df is None or progress_df.empty:
        return set()

    if "homework_id" not in progress_df.columns:
        return set()

    rows = progress_df[
        progress_df["homework_id"].astype(str).str.strip() == homework_id
    ]

    completed: Set[int] = set()

    for _, progress_row in rows.iterrows():
        start_value = progress_row.get("completed_start")
        end_value = progress_row.get("completed_end")
        completed_value = progress_row.get("completed_value")

        if pd.notna(start_value) or pd.notna(end_value):
            start_num = _safe_int(
                start_value if pd.notna(start_value) else end_value,
                0,
            )
            end_num = _safe_int(
                end_value if pd.notna(end_value) else start_value,
                0,
            )
            low, high = sorted((start_num, end_num))
            if low > 0 or high > 0:
                completed.update(range(low, high + 1))
            continue

        # percent型など旧データとの互換用。
        if pd.notna(completed_value):
            count = max(_safe_int(completed_value, 0), 0)
            if universe:
                completed.update(sorted(universe)[:count])
            else:
                completed.update(range(1, count + 1))

    return completed & universe if universe else completed


def _build_task_summary(
    homework_df: pd.DataFrame,
    progress_df: pd.DataFrame,
) -> pd.DataFrame:
    rows: List[Dict[str, object]] = []

    for _, task in homework_df.iterrows():
        universe = _task_universe(task)
        completed = _completed_units_for_task(task, progress_df)
        total_units = len(universe) or max(_safe_int(task.get("total_units"), 0), 0)
        completed_count = min(len(completed), total_units) if total_units else len(completed)
        weight = max(_safe_float(task.get("weight_per_unit"), 1.0), 0.0)

        rows.append(
            {
                "homework_id": str(task.get("homework_id", "")).strip(),
                "subject": str(task.get("subject", "")).strip(),
                "task_name": str(task.get("task_name", "")).strip(),
                "unit_type": str(task.get("unit_type", "")).strip().lower(),
                "start_value": _safe_int(task.get("start_value"), 1),
                "end_value": _safe_int(task.get("end_value"), total_units),
                "total_units": total_units,
                "completed_units": completed_count,
                "remaining_units": max(total_units - completed_count, 0),
                "weight_per_unit": weight,
                "total_points": total_units * weight,
                "completed_points": completed_count * weight,
                "progress_pct": (
                    completed_count / total_units * 100.0 if total_units else 0.0
                ),
                "due_date": str(task.get("due_date", "")).strip(),
                "priority": str(task.get("priority", "")).strip(),
                "completion_rule": str(task.get("completion_rule", "")).strip(),
                "note": str(task.get("note", "")).strip(),
                "completed_set": completed,
                "universe": universe,
            }
        )

    return pd.DataFrame(rows)


def _status_from_margin(margin: float) -> Tuple[str, str, str]:
    if margin >= 15.0:
        key = "rainbow"
    elif margin >= 3.0:
        key = "sun"
    elif margin >= -2.0:
        key = "partly"
    elif margin >= -14.0:
        key = "rain"
    else:
        key = "thunder"

    emoji, message = STATUS_MESSAGES[key]
    return key, emoji, message


def _format_units(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.1f}"


def _render_gauge(st, progress_pct: float) -> None:
    pct = max(0.0, min(progress_pct, 100.0))
    st.markdown(
        f"""
<div style="display:flex;justify-content:center;margin:0.5rem 0 1rem 0;">
  <div style="
      width:180px;
      height:180px;
      border-radius:50%;
      background:conic-gradient(#2563eb {pct:.2f}%, #e5e7eb 0);
      display:flex;
      align-items:center;
      justify-content:center;">
    <div style="
        width:132px;
        height:132px;
        border-radius:50%;
        background:white;
        display:flex;
        flex-direction:column;
        align-items:center;
        justify-content:center;
        box-shadow:inset 0 0 0 1px #f1f5f9;">
      <div style="font-size:20px;font-weight:700;">全体進捗</div>
      <div style="font-size:38px;font-weight:800;">{pct:.0f}%</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )



def _render_progress_bar(
    st,
    label: str,
    pct: float,
    detail: str = "",
) -> None:
    safe_pct = max(0.0, min(float(pct), 100.0))
    safe_label = escape(str(label))
    safe_detail = escape(str(detail))
    st.markdown(
        f"""
<div style="margin:0.35rem 0 1rem 0;">
  <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-end;margin-bottom:7px;">
    <div style="font-weight:700;">{safe_label}</div>
    <div style="font-weight:700;">{safe_pct:.0f}%</div>
  </div>
  <div style="width:100%;height:18px;background:#e5e7eb;border-radius:999px;overflow:hidden;">
    <div style="width:{safe_pct:.2f}%;height:100%;background:#2563eb;border-radius:999px;"></div>
  </div>
  <div style="font-size:15px;color:#64748b;margin-top:5px;">{safe_detail}</div>
</div>
""",
        unsafe_allow_html=True,
    )

def _render_status_message(st, status_key: str, emoji: str, message: str) -> None:
    if status_key == "thunder":
        st.error(f"{emoji} {message}")
    elif status_key == "rain":
        st.warning(f"{emoji} {message}")
    else:
        st.success(f"{emoji} {message}")


def _task_label(row: pd.Series) -> str:
    return str(row.get("task_name", "")).strip()


def _subject_sort_key(subject: str) -> Tuple[int, str]:
    try:
        return SUBJECT_ORDER.index(subject), subject
    except ValueError:
        return len(SUBJECT_ORDER), subject



def _priority_rank(value: str) -> int:
    text = str(value).strip().lower()
    return {
        "high": 0,
        "medium": 1,
        "low": 2,
    }.get(text, 9)


def _due_date_sort_value(value: object) -> pd.Timestamp:
    parsed = pd.to_datetime(value, errors="coerce")
    if pd.isna(parsed):
        return pd.Timestamp.max
    return parsed


def _build_quantitative_subject_summary(summary: pd.DataFrame) -> pd.DataFrame:
    """
    「次に進める目安」専用の教科別集計。

    対象:
    - unit_type = page / sheet
    - 残量がある課題

    除外:
    - point / percent / step
    - 英語教材やビブリオバトル、レポートなどの一発型課題

    教科進捗率はポイントではなく、完了単位数 ÷ 総単位数で計算する。
    """
    if summary is None or summary.empty:
        return pd.DataFrame()

    eligible = summary[
        summary["unit_type"].astype(str).str.lower().isin(["page", "sheet"])
    ].copy()

    if eligible.empty:
        return pd.DataFrame()

    rows: List[Dict[str, object]] = []

    for subject, group in eligible.groupby("subject", dropna=False):
        subject_name = str(subject).strip() or "その他"
        total_units = int(group["total_units"].sum())
        completed_units = int(group["completed_units"].sum())
        remaining_units = max(total_units - completed_units, 0)
        progress_pct = (
            completed_units / total_units * 100.0 if total_units > 0 else 0.0
        )

        total_workload = float(
            (group["total_units"] * group["weight_per_unit"]).sum()
        )
        completed_workload = float(
            (group["completed_units"] * group["weight_per_unit"]).sum()
        )
        remaining_workload = max(total_workload - completed_workload, 0.0)

        rows.append(
            {
                "subject": subject_name,
                "total_units": total_units,
                "completed_units": completed_units,
                "remaining_units": remaining_units,
                "progress_pct": progress_pct,
                "total_workload": total_workload,
                "completed_workload": completed_workload,
                "remaining_workload": remaining_workload,
            }
        )

    result = pd.DataFrame(rows)
    if result.empty:
        return result

    return result.sort_values(
        ["progress_pct", "remaining_units", "subject"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def _allocate_subject_workload(
    quantitative_subjects: pd.DataFrame,
    planned_pct: float,
    required_workload: float,
) -> List[Tuple[str, float]]:
    """
    遅れている教科の上位3教科へ必要量を配分する。

    配分基準:
    - 教科進捗率が低い順
    - 予定進捗との差が大きいほど重く配分
    - 基本イメージは50% / 30% / 20%
    - 残量を超えた分は次の教科へ回す
    """
    if (
        quantitative_subjects is None
        or quantitative_subjects.empty
        or required_workload <= 0
    ):
        return []

    candidates = quantitative_subjects[
        quantitative_subjects["remaining_workload"] > 0
    ].copy()

    if candidates.empty:
        return []

    candidates["delay_gap"] = (
        planned_pct - candidates["progress_pct"]
    ).clip(lower=0.0)

    candidates = candidates.sort_values(
        ["progress_pct", "delay_gap", "remaining_workload", "subject"],
        ascending=[True, False, False, True],
    ).head(3)

    if candidates.empty:
        return []

    base_weights = [0.50, 0.30, 0.20][: len(candidates)]
    base_total = sum(base_weights)
    base_weights = [weight / base_total for weight in base_weights]

    delay_values = candidates["delay_gap"].tolist()
    delay_total = sum(delay_values)

    if delay_total > 0:
        delay_weights = [value / delay_total for value in delay_values]
        combined_weights = [
            base * 0.5 + delay * 0.5
            for base, delay in zip(base_weights, delay_weights)
        ]
    else:
        combined_weights = base_weights

    combined_total = sum(combined_weights)
    combined_weights = [
        weight / combined_total for weight in combined_weights
    ]

    allocations: Dict[str, float] = {
        str(row["subject"]): 0.0
        for _, row in candidates.iterrows()
    }

    remaining_to_allocate = float(required_workload)

    for (_, row), weight in zip(candidates.iterrows(), combined_weights):
        subject = str(row["subject"])
        capacity = float(row["remaining_workload"])
        requested = required_workload * weight
        assigned = min(requested, capacity)
        allocations[subject] += assigned
        remaining_to_allocate -= assigned

    # 容量不足で余った分を、残量がある教科へ順番に再配分する。
    if remaining_to_allocate > 1e-9:
        for _, row in candidates.iterrows():
            subject = str(row["subject"])
            capacity = float(row["remaining_workload"])
            room = max(capacity - allocations[subject], 0.0)
            if room <= 0:
                continue
            add = min(room, remaining_to_allocate)
            allocations[subject] += add
            remaining_to_allocate -= add
            if remaining_to_allocate <= 1e-9:
                break

    return [
        (subject, workload)
        for subject, workload in allocations.items()
        if workload > 1e-9
    ]


def _task_recommendations_for_subject(
    summary: pd.DataFrame,
    subject: str,
    target_workload: float,
) -> List[Dict[str, object]]:
    """
    教科へ割り当てた内部負荷を、実際のページ・枚数へ変換する。

    課題の選択順:
    1. priority
    2. due_date
    3. 現在の進捗率
    4. Homeworkの表示順
    """
    if target_workload <= 0:
        return []

    tasks = summary[
        (summary["subject"].astype(str) == str(subject))
        & summary["unit_type"].astype(str).str.lower().isin(["page", "sheet"])
        & (summary["remaining_units"] > 0)
    ].copy()

    if tasks.empty:
        return []

    tasks["_priority_rank"] = tasks["priority"].map(_priority_rank)
    tasks["_due_sort"] = tasks["due_date"].map(_due_date_sort_value)
    tasks = tasks.sort_values(
        ["_priority_rank", "_due_sort", "progress_pct", "task_name"],
        ascending=[True, True, True, True],
    )

    recommendations: List[Dict[str, object]] = []
    remaining_workload = float(target_workload)

    for _, task in tasks.iterrows():
        if remaining_workload <= 1e-9:
            break

        remaining_units = int(task["remaining_units"])
        if remaining_units <= 0:
            continue

        weight_per_unit = max(float(task["weight_per_unit"]), 0.0001)
        needed_units = max(
            1,
            int(math.ceil(remaining_workload / weight_per_unit)),
        )
        units = min(needed_units, remaining_units)

        recommendations.append(
            {
                "subject": str(task["subject"]),
                "task_name": str(task["task_name"]),
                "unit_type": str(task["unit_type"]).lower(),
                "units": units,
                "workload": units * weight_per_unit,
            }
        )
        remaining_workload -= units * weight_per_unit

    return recommendations


def _build_recovery_recommendations(
    summary: pd.DataFrame,
    planned_pct: float,
) -> Tuple[
    pd.DataFrame,
    List[Dict[str, object]],
    float,
    float,
    float,
]:
    """
    定量課題のみを対象に、予定ラインへ戻すための目安を作る。

    戻り値:
    - 教科別定量進捗
    - 課題別おすすめ
    - 現在の定量進捗率
    - 予定到達までに必要な内部負荷
    - おすすめ実施後の予測進捗率
    """
    quantitative_subjects = _build_quantitative_subject_summary(summary)

    eligible = summary[
        summary["unit_type"].astype(str).str.lower().isin(["page", "sheet"])
    ].copy()

    if eligible.empty:
        return quantitative_subjects, [], 0.0, 0.0, 0.0

    total_workload = float(
        (eligible["total_units"] * eligible["weight_per_unit"]).sum()
    )
    completed_workload = float(
        (eligible["completed_units"] * eligible["weight_per_unit"]).sum()
    )

    quantitative_pct = (
        completed_workload / total_workload * 100.0
        if total_workload > 0
        else 0.0
    )

    target_workload = total_workload * max(planned_pct, 0.0) / 100.0
    required_workload = max(target_workload - completed_workload, 0.0)

    allocations = _allocate_subject_workload(
        quantitative_subjects,
        planned_pct,
        required_workload,
    )

    recommendations: List[Dict[str, object]] = []
    for subject, workload in allocations:
        recommendations.extend(
            _task_recommendations_for_subject(
                summary,
                subject,
                workload,
            )
        )

    recommended_workload = sum(
        float(item["workload"]) for item in recommendations
    )

    expected_pct = (
        min(
            (completed_workload + recommended_workload)
            / total_workload
            * 100.0,
            100.0,
        )
        if total_workload > 0
        else 0.0
    )

    return (
        quantitative_subjects,
        recommendations,
        quantitative_pct,
        required_workload,
        expected_pct,
    )


def _render_recovery_guide(
    st,
    summary: pd.DataFrame,
    planned_pct: float,
) -> None:
    (
        quantitative_subjects,
        recommendations,
        quantitative_pct,
        required_workload,
        expected_pct,
    ) = _build_recovery_recommendations(summary, planned_pct)

    st.subheader("📌 予定ラインに戻すための目安")
    st.caption(
        "ワーク・プリントなど、ページや枚数で管理できる課題だけから自動計算します。"
        "英語教材、ビブリオバトル、レポートなどは含めません。"
    )

    if quantitative_subjects.empty:
        st.info("ページ・枚数で計算できる未完了課題がありません。")
        return

    quantitative_margin = quantitative_pct - planned_pct

    if required_workload <= 1e-9:
        st.success(
            "定量課題は予定ラインに到達しています。"
            "次に進める教科は、体調や予定に合わせて選んでOKです。"
        )
        st.caption(
            f"定量課題の進捗：{quantitative_pct:.1f}% ／ "
            f"予定進捗：{planned_pct:.1f}% ／ "
            f"差：{quantitative_margin:+.1f}%"
        )
        return

    if not recommendations:
        st.info(
            "予定ラインとの差はありますが、具体的なページ・枚数へ変換できる"
            "未完了課題がありません。"
        )
        return

    subject_order: List[str] = []
    for item in recommendations:
        subject = str(item["subject"])
        if subject not in subject_order:
            subject_order.append(subject)

    st.markdown("**優先順位**")
    for index, subject in enumerate(subject_order, start=1):
        subject_row = quantitative_subjects[
            quantitative_subjects["subject"] == subject
        ]
        progress_text = ""
        if not subject_row.empty:
            progress_text = (
                f"（定量課題の進捗 "
                f"{float(subject_row.iloc[0]['progress_pct']):.0f}%）"
            )
        st.write(f"{index}. {subject}{progress_text}")

    st.markdown("**次に進める量の目安**")

    total_display_units = 0
    for item in recommendations:
        unit_type = str(item["unit_type"])
        unit_label = "枚" if unit_type == "sheet" else "ページ"
        units = int(item["units"])
        total_display_units += units
        st.write(
            f"・{item['subject']}／{item['task_name']}："
            f"**{units}{unit_label}**"
        )

    st.markdown(
        f"""
**合計目安：** {total_display_units}ページ・枚  
**この目安を終えた後：** 定量課題の進捗が
**{quantitative_pct:.1f}% → 約{expected_pct:.1f}%**  
予定進捗との差が
**{quantitative_margin:+.1f}% → 約{expected_pct - planned_pct:+.1f}%**
"""
    )

    st.caption(
        "※これは現時点の必要量の目安です。途中で登録すると自動再計算されます。"
        "同じ教科が再び表示された場合は、まだその教科の遅れが残っています。"
        "疲労や予定に応じて別教科へ変更しても問題ありません。"
    )

def render_homework(st, storage) -> None:
    st.header("📚 夏休み課題")
    st.caption("今日やる範囲を明確にして、遠征を除いた実質日数で進捗を管理します。")

    if not hasattr(storage, "supports_homework") or not storage.supports_homework():
        st.error("現在のStorageは宿題管理に対応していません。")
        return

    try:
        homework_df = _normalize_homework(storage.load_all_homework())
        progress_df = _normalize_progress(storage.load_all_homework_progress())
        settings_df = storage.load_all_homework_settings()
    except Exception as exc:
        st.error(f"宿題データを読み込めませんでした：{exc}")
        return

    if homework_df.empty:
        st.warning("Homeworkシートに有効な課題がありません。")
        return

    settings = _settings_dict(settings_df)
    plan_start = _parse_date(
        settings.get("plan_start_date", ""),
        DEFAULT_PLAN_START,
    )
    plan_end = _parse_date(
        settings.get("plan_end_date", ""),
        DEFAULT_PLAN_END,
    )
    study_coach_url = (
        settings.get("study_coach_url", "").strip()
        or DEFAULT_STUDY_COACH_URL
    )

    summary = _build_task_summary(homework_df, progress_df)

    total_points = float(summary["total_points"].sum()) if not summary.empty else 0.0
    completed_points = (
        float(summary["completed_points"].sum()) if not summary.empty else 0.0
    )
    overall_pct = completed_points / total_points * 100.0 if total_points else 0.0

    today = date.today()
    total_available_days, remaining_days, planned_pct = _schedule_metrics(
        today,
        plan_start,
        plan_end,
    )
    margin = overall_pct - planned_pct
    status_key, status_emoji, status_message = _status_from_margin(margin)

    remaining_points = max(total_points - completed_points, 0.0)
    required_daily_pace = (
        remaining_points / remaining_days if remaining_days > 0 else remaining_points
    )

    _render_gauge(st, overall_pct)

    st.markdown(
        f"""
<div style="display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:8px 0 18px 0;">
  <div style="border:1px solid #e5e7eb;border-radius:14px;padding:14px;background:#ffffff;">
    <div style="font-size:15px;color:#64748b;">残り学習可能日</div>
    <div style="font-size:28px;font-weight:800;margin-top:4px;">{remaining_days}日</div>
  </div>
  <div style="border:1px solid #e5e7eb;border-radius:14px;padding:14px;background:#ffffff;">
    <div style="font-size:15px;color:#64748b;">予定進捗</div>
    <div style="font-size:28px;font-weight:800;margin-top:4px;">{planned_pct:.0f}%</div>
  </div>
  <div style="border:1px solid #e5e7eb;border-radius:14px;padding:14px;background:#ffffff;">
    <div style="font-size:15px;color:#64748b;">余裕度差</div>
    <div style="font-size:28px;font-weight:800;margin-top:4px;">{margin:+.1f}%</div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    _render_status_message(st, status_key, status_emoji, status_message)

    st.markdown(
        f"""
**残りポイント：** {_format_units(remaining_points)} / {_format_units(total_points)}  
**今日から必要な平均ペース：** 1学習可能日あたり **{required_daily_pace:.1f}ポイント**
"""
    )

    st.caption(
        f"計画期間：{plan_start:%Y-%m-%d}〜{plan_end:%Y-%m-%d} ／ "
        f"実質学習可能日数：{total_available_days}日"
    )
    st.caption(
        f"※{NON_STUDY_START:%m/%d}〜{NON_STUDY_END:%m/%d}の"
        "サッカー遠征9日間は、予定進捗と残り日数から除外しています。"
    )

    st.divider()
    st.subheader("教科別進捗")

    subject_rows: List[Tuple[str, float, float, float]] = []
    for subject, group in summary.groupby("subject", dropna=False):
        subject_name = str(subject).strip() or "その他"
        subject_total = float(group["total_points"].sum())
        subject_done = float(group["completed_points"].sum())
        subject_pct = subject_done / subject_total * 100.0 if subject_total else 0.0
        subject_rows.append((subject_name, subject_done, subject_total, subject_pct))

    for subject, done, total, pct in sorted(
        subject_rows,
        key=lambda x: _subject_sort_key(x[0]),
    ):
        _render_progress_bar(
            st,
            subject,
            pct,
            f"{_format_units(done)} / {_format_units(total)}ポイント",
        )

    st.divider()
    _render_recovery_guide(
        st,
        summary,
        planned_pct,
    )

    st.divider()
    st.subheader("今日の完了を登録")

    selected_date = st.date_input(
        "実施日",
        value=date.today(),
        max_value=date.today(),
        key="homework_progress_date",
    )
    st.caption("通常は今日のままでOK。過去分を後から登録するときだけ変更してください。")

    subjects = sorted(
        [str(v).strip() for v in summary["subject"].dropna().unique() if str(v).strip()],
        key=_subject_sort_key,
    )
    selected_subject = st.selectbox(
        "教科",
        subjects,
        key="homework_subject",
    )

    subject_tasks = summary[summary["subject"] == selected_subject].copy()
    task_records = subject_tasks.to_dict("records")
    task_names = [str(row["task_name"]) for row in task_records]

    selected_task_name = st.selectbox(
        "課題",
        task_names,
        key="homework_task",
    )
    selected_task = next(
        row for row in task_records if str(row["task_name"]) == selected_task_name
    )

    unit_type = str(selected_task["unit_type"]).lower()
    unit_label = UNIT_LABELS.get(unit_type, "単位")
    start_min = int(selected_task["start_value"])
    end_max = int(selected_task["end_value"])

    if end_max < start_min:
        start_min = 1
        end_max = max(int(selected_task["total_units"]), 1)

    completed_set = set(selected_task["completed_set"])
    available_units = [
        value for value in range(start_min, end_max + 1)
        if value not in completed_set
    ]

    st.caption(
        f"現在：{selected_task['completed_units']} / "
        f"{selected_task['total_units']} {unit_label}"
    )

    if selected_task["completion_rule"]:
        with st.expander("完了条件", expanded=False):
            st.write(selected_task["completion_rule"])

    if not available_units:
        st.success("この課題は完了しています。")
    else:
        default_start = available_units[0]
        default_end = default_start

        c1, c2 = st.columns(2)
        completed_start = c1.selectbox(
            f"開始{unit_label}",
            list(range(start_min, end_max + 1)),
            index=max(default_start - start_min, 0),
            key="homework_completed_start",
        )
        end_candidates = list(range(int(completed_start), end_max + 1))
        completed_end = c2.selectbox(
            f"終了{unit_label}",
            end_candidates,
            index=0,
            key="homework_completed_end",
        )

        duplicate_units = sorted(
            set(range(int(completed_start), int(completed_end) + 1))
            & completed_set
        )
        new_units = sorted(
            set(range(int(completed_start), int(completed_end) + 1))
            - completed_set
        )

        if duplicate_units:
            st.info(
                "すでに完了済みの範囲は二重加算しません。"
                f"今回新しく加算されるのは {len(new_units)} {unit_label}です。"
            )

        if st.button(
            "完了として登録",
            type="primary",
            use_container_width=True,
            key="homework_save_progress",
        ):
            if not new_units:
                st.warning("選択範囲はすべて登録済みです。")
            else:
                now = datetime.now()
                progress_id = (
                    f"HP-{selected_date:%Y%m%d}-"
                    f"{now:%H%M%S}-{uuid.uuid4().hex[:4].upper()}"
                )

                row = {
                    "progress_id": progress_id,
                    "homework_id": selected_task["homework_id"],
                    "progress_date": str(selected_date),
                    "completed_start": int(completed_start),
                    "completed_end": int(completed_end),
                    "completed_value": "",
                    "source": "app",
                    "note": "",
                    "created_at": now.strftime("%Y-%m-%d %H:%M:%S"),
                }

                try:
                    storage.append_homework_progress_row(row)
                    st.success(
                        f"{selected_task_name}："
                        f"{completed_start}〜{completed_end}を登録しました。"
                    )
                    st.rerun()
                except Exception as exc:
                    st.error(f"保存できませんでした：{exc}")

    st.divider()
    st.subheader("課題一覧")

    for _, task in summary.iterrows():
        unit_label = UNIT_LABELS.get(str(task["unit_type"]).lower(), "単位")
        due_text = task["due_date"] or "未設定"
        with st.expander(
            f"{task['subject']}｜{task['task_name']}｜{task['progress_pct']:.0f}%",
            expanded=False,
        ):
            _render_progress_bar(
                st,
                task["task_name"],
                float(task["progress_pct"]),
                f"完了：{task['completed_units']} / {task['total_units']} {unit_label}",
            )
            st.write(f"残り：{task['remaining_units']} {unit_label}")
            st.write(f"提出・確認日：{due_text}")
            if task["completion_rule"]:
                st.write(f"完了条件：{task['completion_rule']}")
            if task["note"]:
                st.caption(task["note"])

    st.divider()
    st.subheader("📷 分からない問題はTeacher Mikel Artetaへ")

    st.info(
        "問題全体と自分の答えが写るように撮影して、"
        "希望するモードと一緒に送ってください。"
    )
    st.markdown(
        """
**送信例**

- 数学、① ヒントだけ
- 理科、③ 答え合わせ
- 英語、④ 間違えた原因
- 社会、⑤ 似た問題を1問
"""
    )

    st.link_button(
        "Teacher Mikel Artetaを開く",
        study_coach_url,
        use_container_width=True,
    )