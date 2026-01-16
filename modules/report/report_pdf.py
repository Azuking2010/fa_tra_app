# modules/report/report_pdf.py
from __future__ import annotations

from io import BytesIO
from typing import Any, Dict, List, Optional

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader


def _fig_to_png_bytes(fig) -> bytes:
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=160, bbox_inches="tight")
    buf.seek(0)
    return buf.read()


def build_report_pdf_bytes(
    title: str,
    period_text: str,
    figs: List[Any],
    footer_text: str = "",
) -> bytes:
    """
    UIで生成した matplotlib Figure をそのままPDFへ貼り付ける（UX=見てるものがレポート）
    """
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4

    # --- Page 1: cover ---
    c.setFont("Helvetica-Bold", 18)
    c.drawString(40, h - 60, title)

    c.setFont("Helvetica", 12)
    c.drawString(40, h - 90, period_text)

    if footer_text:
        c.setFont("Helvetica", 9)
        c.drawString(40, 40, footer_text)

    c.showPage()

    # --- Next pages: figures (1 figure per page) ---
    for fig in figs:
        img_bytes = _fig_to_png_bytes(fig)
        img = ImageReader(BytesIO(img_bytes))

        # ページ余白を少し取って最大表示
        margin = 36
        avail_w = w - margin * 2
        avail_h = h - margin * 2

        # 画像の縦横比を保ってフィット
        # ImageReader から直接サイズが取れない場合があるため、reportlab側に任せつつ横基準で配置
        c.drawImage(img, margin, margin, width=avail_w, height=avail_h, preserveAspectRatio=True, anchor="c")

        c.showPage()

    c.save()
    buf.seek(0)
    return buf.read()
