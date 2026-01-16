import streamlit as st
from datetime import date

from .report_logic import build_report  # 既存想定：期間で report dict を作る
from .report_pdf import build_report_pdf_bytes
from .report_json import build_report_json_bytes

from . import report_charts


def render_report(st, storage):
    st.subheader("レポート（グラフ＆出力）")

    # matplotlib が無い環境でもアプリ全体を落とさない
    if not report_charts.HAS_MPL:
        st.error("レポート描画には matplotlib が必要です。requirements.txt に 'matplotlib' を追加してください。")
        st.stop()

    # 期間選択（UIの真実 → PDF/JSONへ）
    c1, c2 = st.columns(2)
    start_date = c1.date_input("開始日", value=date.today().replace(day=1), key="rp_start")
    end_date = c2.date_input("終了日", value=date.today(), key="rp_end")

    if start_date > end_date:
        st.warning("開始日が終了日より後になっています。")
        st.stop()

    # 集計（UI=truth）
    # build_report は report_logic 側で「portfolio/roadmapの抽出・整形」を担当する想定
    report = build_report(storage, start_date, end_date)

    # 期待：report["df"] が期間内portfolio dataframe（date列あり）
    df = report.get("df")

    st.markdown("## P.2 フィジカル・陸上")
    fig_body = report_charts.build_body_chart(df)
    st.pyplot(fig_body, use_container_width=True)

    fig_50 = report_charts.build_run_chart(df, "run_100m_sec", "50m（sec）", "sec")
    st.pyplot(fig_50, use_container_width=True)

    fig_1500 = report_charts.build_run_chart(df, "run_1500m_sec", "1500m（sec）", "sec")
    st.pyplot(fig_1500, use_container_width=True)

    fig_3000 = report_charts.build_run_chart(df, "run_3000m_sec", "3000m（sec）", "sec")
    st.pyplot(fig_3000, use_container_width=True)

    st.markdown("## P.3 学業")
    fig_school1 = report_charts.build_school_overview_chart(df)
    st.pyplot(fig_school1, use_container_width=True)

    fig_school2 = report_charts.build_school_scores_chart(df)
    st.pyplot(fig_school2, use_container_width=True)

    # コメント系（report_logic側で items を作っている想定）
    comments = report.get("comments", [])
    if comments:
        st.markdown("### コメント（抜粋）")
        for item in comments:
            # item: {"text": "...", "achieved": True/False} 想定
            text = str(item.get("text", "")).strip()
            if not text:
                continue
            achieved = bool(item.get("achieved", False))
            st.checkbox(text, value=achieved, disabled=True)

    st.divider()

    # 出力（見ているUIをそのまま）
    # PDF/JSONは report dict から生成（図も必要ならreportに格納する設計へ拡張可能）
    c3, c4 = st.columns(2)

    with c3:
        pdf_bytes = build_report_pdf_bytes(report)
        st.download_button(
            label="PDFをダウンロード",
            data=pdf_bytes,
            file_name="portfolio_report.pdf",
            mime="application/pdf",
            use_container_width=True,
        )

    with c4:
        json_bytes = build_report_json_bytes(report)
        st.download_button(
            label="JSONをダウンロード（AI向け）",
            data=json_bytes,
            file_name="portfolio_report.json",
            mime="application/json",
            use_container_width=True,
        )
