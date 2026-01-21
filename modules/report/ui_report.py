# modules/report/ui_report.py
from __future__ import annotations

from typing import Any, Optional

import streamlit as st

from .report_logic import build_report_data
from . import report_charts


def render_report(storage: Any, *, roadmap_storage: Optional[Any] = None) -> None:
    """
    レポート画面描画（import-time 副作用ゼロ）

    storage:
      - load_all_portfolio() を持つ想定

    roadmap_storage（任意）:
      - load_all() を持つ想定（Google SheetsのROADMAP）
      - 渡されない場合は roadmap 無しで動作
    """
    st.title("レポート")

    # 期間入力（既存UIに合わせて調整してOK）
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日", value=None)
    with col2:
        end_date = st.date_input("終了日", value=None)

    # データ読み込み（ここで例外が起きても画面で見えるように）
    try:
        portfolio_df = storage.load_all_portfolio() if storage is not None else None
    except Exception as e:
        st.error(f"portfolio 読み込みに失敗: {e}")
        return

    roadmap_df = None
    if roadmap_storage is not None:
        try:
            roadmap_df = roadmap_storage.load_all()
        except Exception as e:
            st.warning(f"ROADMAP 読み込みに失敗（続行）: {e}")
            roadmap_df = None

    # 共通“真実”
    rd = build_report_data(
        portfolio_df=portfolio_df,
        roadmap_df=roadmap_df,
        start_date=start_date,
        end_date=end_date,
    )

    # 期間表記
    period_text = f"{rd.meta.get('start_date','')} ～ {rd.meta.get('end_date','')}"

    # --- グラフ描画 ---
    # P2: フィジカル
    st.subheader("P2: フィジカル")
    fig = report_charts.fig_physical_height_weight(rd.portfolio, period_text, rd.roadmap_for_month)
    st.pyplot(fig, clear_figure=True)

    # P2: 走力
    st.subheader("P2: 走力")
    fig = report_charts.fig_run_50m(rd.portfolio, period_text, rd.roadmap_for_month)
    st.pyplot(fig, clear_figure=True)

    fig = report_charts.fig_run_1500m(rd.portfolio, period_text, rd.roadmap_for_month)
    st.pyplot(fig, clear_figure=True)

    fig = report_charts.fig_run_3000m(rd.portfolio, period_text, rd.roadmap_for_month)
    st.pyplot(fig, clear_figure=True)

    # P3: 学業（順/偏）
    st.subheader("P3: 学業（順位/偏差値）")
    fig = report_charts.fig_academic_rank_deviation(rd.portfolio, period_text, rd.roadmap_for_month)
    st.pyplot(fig, clear_figure=True)

    # P3: 学業（評点/教科スコア）
    st.subheader("P3: 学業（評点/教科スコア）")
    fig = report_charts.fig_academic_scores(rd.portfolio, period_text, rd.roadmap_for_month)
    st.pyplot(fig, clear_figure=True)
