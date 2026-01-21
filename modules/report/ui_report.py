# modules/report/ui_report.py
"""
UI rendering for Report page.

Keep import side-effects minimal.
"""

from __future__ import annotations

from typing import Any, Dict, List

import streamlit as st

from . import report_charts
from .report_logic import build_report
from .report_pdf import build_report_pdf_bytes
from .report_json import build_report_json_bytes


def render_report() -> None:
    st.title("レポート")

    show_roadmap = st.checkbox("ROADMAP（low/mid/high）の目標帯を重ねて表示", value=True)

    report: Dict[str, Any] = build_report()
    # store some display helpers into report dict
    report["period_text"] = report.get("period_text") or report.get("period_display") or ""

    st.caption("ROADMAP: Sheets 接続OK" if report.get("roadmap_ok") else "ROADMAP: Sheets 未接続/未取得")

    figs: List[Any] = []

    # -------------------------
    # P2: Physical
    # -------------------------
    st.subheader("P2: フィジカル")
    f1 = report_charts.fig_physical_height_weight_bmi(report, show_roadmap=show_roadmap)
    st.pyplot(f1, clear_figure=False)
    figs.append(f1)

    # -------------------------
    # P2: Run
    # -------------------------
    st.subheader("P2: 走力")

    f50 = report_charts.fig_run_metric(
        report,
        metric="run_100m_sec",  # UIは50mだが列名は互換維持
        title="Run: 50m (stored as run_100m_sec)",
        show_roadmap=show_roadmap,
        mmss=False,
    )
    st.pyplot(f50, clear_figure=False)
    figs.append(f50)

    f1500 = report_charts.fig_run_metric(
        report,
        metric="run_1500m_sec",
        title="Run: 1500m",
        show_roadmap=show_roadmap,
        mmss=True,
    )
    st.pyplot(f1500, clear_figure=False)
    figs.append(f1500)

    f3000 = report_charts.fig_run_metric(
        report,
        metric="run_3000m_sec",
        title="Run: 3000m",
        show_roadmap=show_roadmap,
        mmss=True,
    )
    st.pyplot(f3000, clear_figure=False)
    figs.append(f3000)

    # -------------------------
    # P3: Academic
    # -------------------------
    st.subheader("P3: 学業（順位/偏差値）")
    f_rank = report_charts.fig_academic_rank_deviation(report, show_roadmap=show_roadmap)
    st.pyplot(f_rank, clear_figure=False)
    figs.append(f_rank)

    st.subheader("P3: 学業（評点/教科スコア）")
    f_score = report_charts.fig_academic_rating_scores(report, show_roadmap=show_roadmap)
    st.pyplot(f_score, clear_figure=False)
    figs.append(f_score)

    # -------------------------
    # Export
    # -------------------------
    st.divider()

    footer = report.get("footer_text") or ""
    pdf_bytes = build_report_pdf_bytes(
        title="FA期間 自主トレレポート",
        period_text=report.get("period_text") or "",
        figs=figs,
        footer_text=footer,
    )
    st.download_button(
        label="PDFをダウンロード",
        data=pdf_bytes,
        file_name="portfolio_report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )

    json_bytes = build_report_json_bytes(report)
    st.download_button(
        label="JSONをダウンロード（AI向け）",
        data=json_bytes,
        file_name="portfolio_report.json",
        mime="application/json",
        use_container_width=True,
    )
