"""
PDF filler for the summer training request form.

The source PDF has no form fields — text is overlaid at hardcoded coordinates.
Arabic text requires reshaping (letter joining) + bidi (RTL direction) before
passing to reportlab, otherwise letters render disconnected and in wrong order.

Coordinate system: reportlab uses bottom-left origin (y=0 at bottom).
PDF page height = 841.92 pts. To convert from top-origin bbox coords:
    reportlab_y = PAGE_HEIGHT - bbox_yMax

To calibrate field positions run:  python -m tests.test_pdf
"""

import io
import os
import warnings
from dataclasses import dataclass
from datetime import date
from typing import List, Optional

import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.utils import ImageReader
from pypdf import PdfReader, PdfWriter

with warnings.catch_warnings():
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    from hijri_converter import convert as _hijri_convert

from bot.config import FONT_PATH, FONT_BOLD_PATH, PDF_FORM_PATH

PAGE_WIDTH, PAGE_HEIGHT = A4  # 595.28 x 841.89

FONT_NAME      = "Amiri"
FONT_NAME_BOLD = "AmiriBold"

# ── Field coordinate map ────────────────────────────────────────────────────
# x     = horizontal anchor point
# y     = reportlab y from bottom (PAGE_HEIGHT − bbox_yMax)
# align = "right" | "center" | "left"
# size  = font size in pts
# bold  = use bold font (optional)
# ──────────────────────────────────────────────────────────────────────────
FIELDS: dict[str, dict] = {
    # Student data table — row 1
    "full_name":           {"x": 452, "y": 671, "align": "right",  "size": 11},
    "university_id":       {"x": 183, "y": 671, "align": "right",  "size": 11},
    # Student data table — row 2
    "department":          {"x": 466, "y": 653, "align": "right",  "size": 11},
    "remaining_hours":     {"x": 148, "y": 653, "align": "right",  "size": 11},
    # Company name — first dashed line under the request sentence
    "company_name":        {"x": 540, "y": 584, "align": "right",  "size": 11, "bold": True},
    # Optional company description — line below company name
    "company_description": {"x": 540, "y": 566, "align": "right",  "size": 10},
    # Signature — image embedded if available; field kept for text fallback
    "signature":           {"x": 280, "y": 435, "align": "right",  "size": 10},
    # Hijri date — format: التاريخ: [day] / [month] / 14[year] هـ
    "date_day":            {"x": 112, "y": 435, "align": "center", "size": 10, "bold": True},
    "date_month":          {"x": 95,  "y": 435, "align": "center", "size": 10, "bold": True},
    "date_year_last2":     {"x": 75,  "y": 435, "align": "left",   "size": 10, "bold": True},
}


def _register_fonts() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        if not os.path.exists(FONT_PATH):
            raise FileNotFoundError(
                f"Arabic font not found at {FONT_PATH}. Run: docker compose build"
            )
        pdfmetrics.registerFont(TTFont(FONT_NAME, FONT_PATH))

    if FONT_NAME_BOLD not in pdfmetrics.getRegisteredFontNames():
        if not os.path.exists(FONT_BOLD_PATH):
            raise FileNotFoundError(
                f"Arabic bold font not found at {FONT_BOLD_PATH}. Run: docker compose build"
            )
        pdfmetrics.registerFont(TTFont(FONT_NAME_BOLD, FONT_BOLD_PATH))


def _ar(text: str) -> str:
    """Reshape + apply bidi so reportlab renders Arabic correctly (LTR visual order)."""
    return get_display(arabic_reshaper.reshape(str(text)))


def _draw_field(c: canvas.Canvas, key: str, value: str) -> None:
    cfg = FIELDS[key]
    font = FONT_NAME_BOLD if cfg.get("bold") else FONT_NAME
    c.setFont(font, cfg["size"])
    text = _ar(value)
    x, y, align = cfg["x"], cfg["y"], cfg["align"]
    if align == "right":
        c.drawRightString(x, y, text)
    elif align == "center":
        c.drawCentredString(x, y, text)
    else:
        c.drawString(x, y, text)


def _wrap_words(text: str, font: str, size: int, max_width: int) -> List[str]:
    """Split text into lines that fit within max_width pts."""
    from reportlab.pdfbase.pdfmetrics import stringWidth
    words = text.split()
    lines: List[str] = []
    current: List[str] = []
    for word in words:
        candidate = " ".join(current + [word])
        if stringWidth(_ar(candidate), font, size) <= max_width:
            current.append(word)
        else:
            if current:
                lines.append(" ".join(current))
            current = [word]
    if current:
        lines.append(" ".join(current))
    return lines or [text]


def _draw_wrapped_field(c: canvas.Canvas, key: str, value: str, max_width: int = 450) -> None:
    """Draw text with automatic word wrapping, lines going downward."""
    cfg = FIELDS[key]
    font = FONT_NAME_BOLD if cfg.get("bold") else FONT_NAME
    size = cfg["size"]
    c.setFont(font, size)
    x, y, align = cfg["x"], cfg["y"], cfg["align"]
    line_height = size + 3
    for i, line in enumerate(_wrap_words(value, font, size, max_width)):
        shaped = _ar(line)
        draw_y = y - i * line_height
        if align == "right":
            c.drawRightString(x, draw_y, shaped)
        elif align == "center":
            c.drawCentredString(x, draw_y, shaped)
        else:
            c.drawString(x, draw_y, shaped)


def _draw_signature_image(c: canvas.Canvas, image_path: str) -> None:
    """Embed a drawn signature image at the signature field location."""
    cfg = FIELDS["signature"]
    try:
        img = ImageReader(image_path)
        w, h = 130, 50  # pts — run test_pdf.py to recalibrate if needed
        x = cfg["x"] - w / 2
        y = cfg["y"] - h / 2
        c.drawImage(img, x, y, width=w, height=h, mask="auto", preserveAspectRatio=True)
    except Exception:
        pass


@dataclass
class FormData:
    full_name: str
    university_id: str
    department: str
    remaining_hours: str
    company_name: str
    signature: str = ""                        # legacy text (unused)
    company_description: Optional[str] = None  # optional second line under company name
    signature_image_path: Optional[str] = None # path to drawn PNG/JPG signature
    request_date: Optional[date] = None        # defaults to today


def _hijri_today(d: date) -> tuple[str, str, str]:
    """Return (day, month, year_last2) in Hijri for the given Gregorian date."""
    h = _hijri_convert.Gregorian(d.year, d.month, d.day).to_hijri()
    return str(h.day), str(h.month), str(h.year)[-2:]


def _build_overlay(data: FormData) -> io.BytesIO:
    """Build the text overlay as an in-memory PDF."""
    req_date = data.request_date or date.today()
    day, month, year_last2 = _hijri_today(req_date)

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)

    _draw_field(c, "full_name",       data.full_name)
    _draw_field(c, "university_id",   data.university_id)
    _draw_field(c, "department",      data.department)
    _draw_field(c, "remaining_hours", data.remaining_hours)
    _draw_field(c, "company_name",    data.company_name)

    if data.company_description:
        _draw_wrapped_field(c, "company_description", data.company_description)

    if data.signature_image_path and os.path.exists(data.signature_image_path):
        _draw_signature_image(c, data.signature_image_path)
    elif data.signature:
        _draw_field(c, "signature", data.signature)

    _draw_field(c, "date_day",        day)
    _draw_field(c, "date_month",      month)
    _draw_field(c, "date_year_last2", year_last2)

    c.save()
    buf.seek(0)
    return buf


def _merge(overlay_buf: io.BytesIO) -> PdfWriter:
    base_reader    = PdfReader(PDF_FORM_PATH)
    overlay_reader = PdfReader(overlay_buf)
    writer = PdfWriter()
    page = base_reader.pages[0]
    page.merge_page(overlay_reader.pages[0])
    writer.add_page(page)
    return writer


def fill_form(data: FormData, output_path: str) -> str:
    """Fill the form and write to output_path. Returns output_path."""
    _register_fonts()
    writer = _merge(_build_overlay(data))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "wb") as f:
        writer.write(f)
    return output_path


def fill_form_to_bytes(data: FormData) -> bytes:
    """Fill the form and return the result as raw bytes."""
    _register_fonts()
    writer = _merge(_build_overlay(data))
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()
