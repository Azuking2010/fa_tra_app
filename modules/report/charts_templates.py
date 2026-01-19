# modules/report/charts_templates.py
from __future__ import annotations

from typing import Optional

from .charts_base import (
    require_mpl,
    setup_ax,
    make_period_str,
    annotate_latest,
    make_mmss_formatter,
    fmt_mmss_from_seconds,
    DEFAULT_STYLE,
)

try:
    import matplotlib.pyplot as plt
    HAS_MPL = True
except Exception:
    plt = None
    HAS_MPL = False


def line_chart_1y(
    *,
    dates,
    values,
    title: str,
    ylabel: str,
    period_in_title: bool = True,
    mmss_axis: bool = False,
    latest_label_mode: str = "raw",  # "raw" or "mmss"
):
    """
    折線（1軸）テンプレ
    """
    require_mpl()

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(dates, values, marker="o")

    period = make_period_str(dates) if period_in_title else ""
    if period:
        title2 = f"{title}\n{period}"
    else:
        title2 = title

    setup_ax(ax, title2, ylabel)

    if mmss_axis:
        ax.yaxis.set_major_formatter(make_mmss_formatter())

    # 最新値注釈
    if dates is not None and values is not None and len(dates) > 0:
        x_last = dates.iloc[-1] if hasattr(dates, "iloc") else dates[-1]
        y_last = values[-1] if isinstance(values, list) else (values.iloc[-1] if hasattr(values, "iloc") else values[-1])

        if latest_label_mode == "mmss":
            label = fmt_mmss_from_seconds(y_last)
        else:
            # raw表示（秒なら "294.0s" など）
            try:
                label = f"{float(y_last):.1f}"
            except Exception:
                label = str(y_last)

        annotate_latest(ax, x_last, y_last, label)

    return fig


def line_chart_2y(
    *,
    dates,
    left_series: list[tuple[str, list, dict]],   # [(label, values, plot_kwargs)]
    right_series: list[tuple[str, list, dict]],  # [(label, values, plot_kwargs)]
    title: str,
    ylabel_left: str,
    ylabel_right: str,
    period_in_title: bool = True,
):
    """
    折線（2軸）テンプレ
    """
    require_mpl()

    fig, ax1 = plt.subplots(figsize=(8, 4))
    ax2 = ax1.twinx()
    ax1.right_ax = ax2  # setup_ax 用

    # left plots
    for label, values, kwargs in left_series:
        ax1.plot(dates, values, label=label, **(kwargs or {}))

    # right plots
    for label, values, kwargs in right_series:
        ax2.plot(dates, values, label=label, **(kwargs or {}))

    period = make_period_str(dates) if period_in_title else ""
    if period:
        title2 = f"{title}\n{period}"
    else:
        title2 = title

    setup_ax(ax1, title2, ylabel_left, ylabel_right)

    ax1.legend(loc="upper left", fontsize=DEFAULT_STYLE.legend_fontsize)
    ax2.legend(loc="upper right", fontsize=DEFAULT_STYLE.legend_fontsize)

    return fig
