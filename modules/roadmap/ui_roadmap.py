# modules/roadmap/ui_roadmap.py
from __future__ import annotations

import streamlit as st
from datetime import date

from modules.roadmap.roadmap_storage import build_roadmap_storage
from modules.roadmap.roadmap_logic import pick_active_rows, pick_latest_row, norm_ym


def render_roadmap(st):
    st.subheader("ROADMAP（未来予想図）")

    # storage.py は触らない方針なので、ROADMAPは独立接続
    rm_storage = build_roadmap_storage(st)

    ok, msg = rm_storage.healthcheck()
    if ok:
        st.success(msg)
    else:
        st.error(msg)
        st.info("※ ROADMAPシートの1行目（ヘッダ50項目）が正しいか確認してください。")
        st.stop()

    df = rm_storage.load_all()

    # 表示用：対象年月（ポートフォリオと同じく date_input を使い、YYYY-MMに変換）
    st.markdown("### 対象年月の選択")
    d = st.date_input("日付（この日付の年月でROADMAPを参照）", value=date.today(), key="roadmap_ref_date")
    ym = f"{d.year:04d}-{d.month:02d}"
    st.caption(f"参照年月: {ym}")

    hit = pick_active_rows(df, ym)
    if hit is None or hit.empty:
        st.warning("この年月に該当するROADMAP行がありません。")
    else:
        st.success(f"該当：{len(hit)}件")
        # 複数なら start_ym が一番新しい行を採用して見せる（他も一覧で出す）
        chosen = pick_latest_row(hit)

        with st.expander("この年月の採用行（代表）", expanded=True):
            if chosen is not None:
                st.write(chosen.dropna())
            else:
                st.info("代表行が選べませんでした。")

        with st.expander("該当行の一覧（確認用）", expanded=False):
            st.dataframe(hit, use_container_width=True)

    st.divider()

    st.markdown("### 全件一覧（編集は後で追加できます）")
    st.dataframe(df, use_container_width=True)

    st.caption("※このページは“表示専用”として先に安全に作ってあります。編集UIは次のステップで追加します。")
