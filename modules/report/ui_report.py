# modules/report/ui_report.py
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict

import streamlit as st

from ..storage import Storage
from ..roadmap.roadmap_storage import build_roadmap_storage

from .report_logic import build_report_data
from .report_charts import (
    fig_physical_height_weight,
    fig_run_50m,
    fig_run_1500m,
    fig_run_3000m,
    fig_academic_position,
    fig_academic_scores_rating,
)


def _period_text(s: Any, e: Any) -> str:
    return f"{s} ～ {e}"


def render_report(storage: Storage):
    st.title("レポート")

    # 期間
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("開始日", value=date.today() - timedelta(days=7))
    with col2:
        end_date = st.date_input("終了日", value=date.today())

    # データロード
    portfolio_df = storage.load_all_portfolio()
    roadmap_storage = build_roadmap_storage(storage)
    roadmap_df = None
    try:
        if roadmap_storage is not None:
            roadmap_df = roadmap_storage.load_all()
    except Exception:
        roadmap_df = None

    report = build_report_data(
        portfolio_df=portfolio_df,
        roadmap_df=roadmap_df,
        start_date=start_date,
        end_date=end_date,
    )

    st.caption(f"ROADMAP: Sheets 接続{'OK' if report.meta.get('has_roadmap') else 'NG'}")

    # プロット用のroadmap dict（ym -> rowdict）
    roadmap_for_month = report.roadmap_for_month or {}

    # ポートフォリオから必要カラムを整形（無ければ落とさない）
    df = report.portfolio.copy()

    # ==========
    # P2: フィジカル
    # ==========
    st.subheader("P2: フィジカル")
    fig = fig_physical_height_weight(df, period_text=_period_text(start_date, end_date), roadmap=roadmap_for_month)
    st.pyplot(fig, use_container_width=True)

    # ==========
    # P2: 走力
    # ==========
    st.subheader("P2: 走力")

    fig = fig_run_50m(df, period_text=_period_text(start_date, end_date), roadmap=roadmap_for_month)
    st.pyplot(fig, use_container_width=True)

    fig = fig_run_1500m(df, period_text=_period_text(start_date, end_date), roadmap=roadmap_for_month)
    st.pyplot(fig, use_container_width=True)

    fig = fig_run_3000m(df, period_text=_period_text(start_date, end_date), roadmap=roadmap_for_month)
    st.pyplot(fig, use_container_width=True)

    # ==========
    # P3: 学業
    # ==========
    st.subheader("P3: 学業（順位/偏差値）")
    fig = fig_academic_position(df, period_text=_period_text(start_date, end_date), roadmap=roadmap_for_month)
    st.pyplot(fig, use_container_width=True)

    st.subheader("P3: 学業（評点/教科スコア）")
    fig = fig_academic_scores_rating(df, period_text=_period_text(start_date, end_date), roadmap=roadmap_for_month)
    st.pyplot(fig, use_container_width=True)
