# modules/report/charts_definitions.py
from __future__ import annotations

from .charts_templates import line_chart_1y, line_chart_2y
from .chart_base import to_seconds_series


def fig_physical_height_weight_bmi(report, show_roadmap: bool = True):
    df = report.portfolio
    dates = df["date"]

    left = [
        ("身長 (cm)", df["height_cm"].tolist(), {"color": "tab:blue"}),
    ]

    right = [
        ("体重 (kg)", df["weight_kg"].tolist(), {"color": "tab:orange"}),
    ]
    if "bmi" in df.columns:
        right.append(("BMI", df["bmi"].tolist(), {"color": "tab:green", "linestyle": "--"}))

    return line_chart_2y(
        dates=dates,
        left_series=left,
        right_series=right,
        title="フィジカル推移（身長・体重・BMI）",
        ylabel_left="身長 (cm)",
        ylabel_right="体重 (kg) / BMI",
        period_in_title=True,
    )


def fig_run_metric(report, metric: str, title: str, show_roadmap: bool = True, mmss: bool = False):
    df = report.portfolio
    dates = df["date"]

    values = to_seconds_series(df[metric].tolist(), mmss=mmss)

    # 50m は秒のまま、1500/3000 は mm:ss 表示にする想定
    if mmss:
        ylabel = "タイム（分:秒）"
        latest_mode = "mmss"
        mmss_axis = True
    else:
        ylabel = "タイム（秒）"
        latest_mode = "raw"
        mmss_axis = False

    return line_chart_1y(
        dates=dates,
        values=values,
        title=title,
        ylabel=ylabel,
        period_in_title=True,
        mmss_axis=mmss_axis,
        latest_label_mode=latest_mode,
    )


def fig_academic_position(report, show_roadmap: bool = True):
    df = report.portfolio
    dates = df["date"]

    left = [("学年順位", df["rank"].tolist(), {"color": "tab:red"})]
    right = [("偏差値", df["deviation"].tolist(), {"color": "tab:blue"})]

    return line_chart_2y(
        dates=dates,
        left_series=left,
        right_series=right,
        title="学業推移（順位・偏差値）",
        ylabel_left="学年順位",
        ylabel_right="偏差値",
        period_in_title=True,
    )


def fig_academic_scores_rating(report, show_roadmap: bool = True):
    df = report.portfolio
    dates = df["date"]

    left = [("評点", df["rating"].tolist(), {"color": "black", "linewidth": 2})]

    subject_map = {
        "score_jp": "国語",
        "score_math": "数学",
        "score_en": "英語",
        "score_sci": "理科",
        "score_soc": "社会",
    }
    right = []
    for col, jp in subject_map.items():
        if col in df.columns:
            right.append((jp, df[col].tolist(), {}))

    return line_chart_2y(
        dates=dates,
        left_series=left,
        right_series=right,
        title="学業推移（評点・教科スコア）",
        ylabel_left="評点",
        ylabel_right="得点",
        period_in_title=True,
    )
