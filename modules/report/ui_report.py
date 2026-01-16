# modules/report/ui_report.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, List

import pandas as pd

from modules.roadmap.roadmap_storage import build_roadmap_storage

from .report_logic import build_report_data
from .report_pdf import build_report_pdf_bytes
from .report_json import build_report_json_bytes

# report_charts は matplotlib に依存するので HAS_MPL を見てガードする
from . import report_charts
from .report_charts import (
    fig_physical_height_weight_bmi,
    fig_run_metric,
    fig_academic_position,
    fig_academic_scores_rating,
)


def render_report(st, storage) -> None:
    st.header("レポート / グラフ")

    # matplotlib が無い環境でもアプリ全体を落とさない
    if not getattr(report_charts, "HAS_MPL", False):
        st.error("レポート描画には matplotlib が必要です。requirements.txt（ルート）に 'matplotlib' を追加してください。")
        st.stop()

    # --- Inputs ---
    today = date.today()
    default_start = today - timedelta(days=180)

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日", value=default_start)
    with col2:
        end_date = st.date_input("終了日", value=today)

    if start_date > end_date:
        st.warning("開始日が終了日より後になっています。")
        st.stop()

    show_roadmap = st.checkbox("ROADMAP（low/mid/high）の目標帯を重ねて表示", value=True)

    # --- Load portfolio ---
    try:
        portfolio_df = storage.load_all_portfolio() if storage.supports_portfolio() else pd.DataFrame()
    except Exception:
        portfolio_df = pd.DataFrame()

    # --- Load roadmap (専用 storage を使用) ---
    roadmap_df = pd.DataFrame()
    try:
        rs = build_roadmap_storage(st)
        ok, msg = rs.healthcheck()
        st.caption(msg)
        if ok:
            roadmap_df = rs.load_all()
    except Exception:
        roadmap_df = pd.DataFrame()

    report = build_report_data(
        portfolio_df=portfolio_df,
        roadmap_df=roadmap_df,
        start_date=start_date,
        end_date=end_date,
    )

    if report.portfolio.empty:
        st.warning("指定期間の portfolio データがありません。期間を調整してください。")
        st.stop()

    # --- Charts (UI=truth) ---
    figs: List[Any] = []

    st.subheader("P2: フィジカル")
    f1 = fig_physical_height_weight_bmi(report, show_roadmap=show_roadmap)
    st.pyplot(f1, clear_figure=False)
    figs.append(f1)

    st.subheader("P2: 走力")
    f50 = fig_run_metric(
        report,
        metric="run_100m_sec",  # UIは50mだが列名は互換維持
        title="Run: 50m (stored as run_100m_sec)",
        show_roadmap=show_roadmap,
        mmss=False,
    )
    st.pyplot(f50, clear_figure=False)
    figs.append(f50)

    f1500 = fig_run_metric(
        report,
        metric="run_1500m_sec",
        title="Run: 1500m",
        show_roadmap=show_roadmap,
        mmss=True,
    )
    st.pyplot(f1500, clear_figure=False)
    figs.append(f1500)

    f3000 = fig_run_metric(
        report,
        metric="run_3000m_sec",
        title="Run: 3000m",
        show_roadmap=show_roadmap,
        mmss=True,
    )
    st.pyplot(f3000, clear_figure=False)
    figs.append(f3000)

    st.subheader("P3: 学業（順位/偏差値）")
    fa1 = fig_academic_position(report, show_roadmap=show_roadmap)
    st.pyplot(fa1, clear_figure=False)
    figs.append(fa1)

    st.subheader("P3: 学業（評点/教科スコア）")
    fa2 = fig_academic_scores_rating(report, show_roadmap=show_roadmap)
    st.pyplot(fa2, clear_figure=False)
    figs.append(fa2)

    # --- Exports ---
    st.divider()
    st.subheader("出力")

    title = "Portfolio Report"
    period_text = f"Period: {start_date} - {end_date}"
    footer = "Generated from UI figures / JSON is for AI analysis."

    pdf_bytes = build_report_pdf_bytes(
        title=title,
        period_text=period_text,
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
