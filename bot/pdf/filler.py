"""
PDF filler for the summer training request form.

The source PDF has no form fields — text is overlaid at hardcoded coordinates.
Arabic text requires reshaping (letter joining) + bidi (RTL direction) before
passing to reportlab, otherwise letters render disconnected and in wrong order.

Coordinate system: reportlab uses bottom-left origin (y=0 at bottom).
PDF page height = 841.92 pts. To convert from top-origin bbox coords:
    reportlab_y = PAGE_HEIGHT - bbox_yMax
"""

import io
import os
from dataclasses import dataclass
from datetime import date
from typing import Optional

import arabic_reshaper
from bidi.algorithm import get_display
from hijri_converter import convert
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader, PdfWriter

from bot.config import FONT_PATH, PDF_FORM_PATH

PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.28 x 841.89

FONT_NAME = "Amiri"

# ---------------------------------------------------------------------------
# Field coordinate map
# Each entry: x = horizontal anchor, y = reportlab y (from bottom),
#             align = "right" | "center" | "left", size = font size in pts
# ---------------------------------------------------------------------------
FIELDS: dict[str, dict] = {
    "full_name":       {"x": 477, "y": 671, "align": "right",  "size": 11},
    "university_id":   {"x": 213, "y": 671, "align": "right",  "size": 11},
    "department":      {"x": 491, "y": 653, "align": "right",  "size": 11},
    "remaining_hours": {"x": 173, "y": 653, "align": "right",  "size": 11},
    "company_name":    {"x": 553, "y": 573, "align": "right",  "size": 11},
    "signature":       {"x": 284, "y": 435, "align": "right",  "size": 10},
    "date_day":        {"x": 122, "y": 435, "align": "center", "size": 10},
    "date_month":      {"x": 95,  "y": 435, "align": "center", "size": 10},
    "date_year_last2": {"x": 74,  "y": 435, "align": "center", "size": 10},
}


def _register_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        if not os.path.exists(FONT_PATH):
            raise FileNotFoundError(
                f"Arabic font not found at {FONT_PATH}. "
                "Run: docker compose build  (font is downloaded during build)"
            )
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))


def _ar(text: str) -> str:
    """Reshape + apply bidi so reportlab renders Arabic correctly."""
    reshaped = arabic_reshaper.reshape(str(text))
    return get_display(reshaped)


def _draw_field(c: canvas.Canvas, key: str, value: str) -> None:
    cfg = FIELDS[key]
    c.setFont(FONT_NAME, cfg["size"])
    text = _ar(value)
    x, y, align = cfg["x"], cfg["y"], cfg["align"]
    if align == "right":
        c.drawRightString(x, y, text)
    elif align == "center":
        c.drawCentredString(x, y, text)
    else:
        c.drawString(x, y, text)


@dataclass
class FormData:
    full_name: str
    university_id: str
    department: str
    remaining_hours: str
    company_name: str
    signature: str
    request_date: Optional[date] = None  # defaults to today


def _hijri_today(d: date) -> tuple[str, str, str]:
    """Return (day, month, year_last2) in Hijri."""
    h = convert.Gregorian(d.year, d.month, d.day).to_hijri()
    return str(h.day), str(h.month), str(h.year)[-2:]


def fill_form(data: FormData, output_path: str) -> str:
    """
    Fill the training request PDF with the given data.
    Writes the result to output_path and returns output_path.
    """
    _register_font()

    req_date = data.request_date or date.today()
    day, month, year_last2 = _hijri_today(req_date)

    # Build an overlay PDF in memory
    overlay_buffer = io.BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=A4)

    _draw_field(c, "full_name",       data.full_name)
    _draw_field(c, "university_id",   data.university_id)
    _draw_field(c, "department",      data.department)
    _draw_field(c, "remaining_hours", data.remaining_hours)
    _draw_field(c, "company_name",    data.company_name)
    _draw_field(c, "signature",       data.signature)
    _draw_field(c, "date_day",        day)
    _draw_field(c, "date_month",      month)
    _draw_field(c, "date_year_last2", year_last2)

    c.save()
    overlay_buffer.seek(0)

    # Merge overlay onto the original form
    base_reader = PdfReader(PDF_FORM_PATH)
    overlay_reader = PdfReader(overlay_buffer)

    writer = PdfWriter()
    base_page = base_reader.pages[0]
    base_page.merge_page(overlay_reader.pages[0])
    writer.add_page(base_page)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path


def fill_form_to_bytes(data: FormData) -> bytes:
    """Fill the form and return the result as bytes (for sending via Telegram)."""
    _register_font()

    req_date = data.request_date or date.today()
    day, month, year_last2 = _hijri_today(req_date)

    overlay_buffer = io.BytesIO()
    c = canvas.Canvas(overlay_buffer, pagesize=A4)

    _draw_field(c, "full_name",       data.full_name)
    _draw_field(c, "university_id",   data.university_id)
    _draw_field(c, "department",      data.department)
    _draw_field(c, "remaining_hours", data.remaining_hours)
    _draw_field(c, "company_name",    data.company_name)
    _draw_field(c, "signature",       data.signature)
    _draw_field(c, "date_day",        day)
    _draw_field(c, "date_month",      month)
    _draw_field(c, "date_year_last2", year_last2)

    c.save()
    overlay_buffer.seek(0)

    base_reader = PdfReader(PDF_FORM_PATH)
    overlay_reader = PdfReader(overlay_buffer)

    writer = PdfWriter()
    base_page = base_reader.pages[0]
    base_page.merge_page(overlay_reader.pages[0])
    writer.add_page(base_page)

    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
