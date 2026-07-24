"""Route export to PDF and Excel (F5, docs/ARCHITECTURE.md §2.2 export).

Produces a driver-facing sheet: ordered stops with address, order ref, time
window, weight and phone. Excel handles Arabic addresses natively; the PDF
reshapes Arabic (arabic-reshaper + python-bidi) and renders it with a bundled
Unicode font (DejaVuSans, which covers Latin + Arabic presentation forms). Drop
a Naskh font (Amiri / Noto Naskh Arabic, OFL) into assets/ for nicer glyphs —
the code uses whatever font is registered; Latin is unaffected.
"""

import io
import uuid
from pathlib import Path
from typing import Any

import arabic_reshaper
from bidi.algorithm import get_display
from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from routeopt.models.delivery import Delivery
from routeopt.models.route import Route

_HEADERS = ["#", "Adresse", "Commande", "Fenêtre", "Poids (kg)", "Téléphone"]

# Register a Unicode font covering Latin + Arabic; fall back to Helvetica if absent.
_FONT_NAME = "Helvetica"
_FONT_PATH = Path(__file__).resolve().parents[2] / "assets" / "DejaVuSans.ttf"
if _FONT_PATH.exists():
    try:
        pdfmetrics.registerFont(TTFont("RouteOptSans", str(_FONT_PATH)))
        _FONT_NAME = "RouteOptSans"
    except Exception:  # pragma: no cover - font load is best-effort
        _FONT_NAME = "Helvetica"


def _is_arabic(text: str) -> bool:
    return any(
        "؀" <= c <= "ۿ"  # Arabic
        or "ݐ" <= c <= "ݿ"  # Arabic Supplement
        or "ﭐ" <= c <= "﷿"  # Presentation Forms-A
        or "ﹰ" <= c <= "﻿"  # Presentation Forms-B
        for c in text
    )


def _shape(text: str) -> str:
    """Reshape + bidi-reorder Arabic for PDF rendering; leave Latin unchanged."""
    if not text or not _is_arabic(text):
        return text
    return str(get_display(arabic_reshaper.reshape(text)))


def _distance_label(route: Route) -> str:
    return f"{float(route.total_distance_m) / 1000:.1f} km" if route.total_distance_m else "—"


def _time_window(delivery: Delivery | None) -> str:
    if delivery and delivery.time_window_start and delivery.time_window_end:
        return (
            f"{delivery.time_window_start.strftime('%H:%M')}"
            f"–{delivery.time_window_end.strftime('%H:%M')}"
        )
    return ""


def _rows(route: Route, deliveries: dict[uuid.UUID, Delivery]) -> list[list[str]]:
    rows: list[list[str]] = []
    for stop in sorted(route.stops, key=lambda s: s.sequence):
        d = deliveries.get(stop.delivery_id)
        rows.append(
            [
                str(stop.sequence + 1),
                d.address if d else str(stop.delivery_id),
                (d.order_id if d and d.order_id else ""),
                _time_window(d),
                (f"{float(d.weight):g}" if d and d.weight is not None else ""),
                (d.customer_phone if d and d.customer_phone else ""),
            ]
        )
    return rows


def build_excel(route: Route, deliveries: dict[uuid.UUID, Delivery]) -> bytes:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tournée"
    ws.append(["RouteOpt — Feuille de tournée"])
    ws.append([f"Tournée {str(route.id)[:8]}", f"Distance: {_distance_label(route)}"])
    ws.append([f"Arrêts: {len(route.stops)}"])
    ws.append([])
    ws.append(_HEADERS)
    for row in _rows(route, deliveries):
        ws.append(row)

    for col, width in zip("ABCDEF", (5, 45, 16, 14, 12, 16), strict=True):
        ws.column_dimensions[col].width = width

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_pdf(route: Route, deliveries: dict[uuid.UUID, Delivery]) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title=f"Tournée {str(route.id)[:8]}")
    styles = getSampleStyleSheet()
    cell = ParagraphStyle("cell", parent=styles["BodyText"], fontName=_FONT_NAME, fontSize=8)

    elements = [
        Paragraph("RouteOpt — Feuille de tournée", styles["Title"]),
        Paragraph(
            f"Tournée {str(route.id)[:8]} · {_distance_label(route)} · {len(route.stops)} arrêts",
            styles["Normal"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    # Reshape Arabic cells for correct PDF rendering; Latin passes through unchanged.
    data: list[list[Any]] = [_HEADERS]
    for row in _rows(route, deliveries):
        shaped = [_shape(str(c)) for c in row]
        data.append(
            [shaped[0], Paragraph(shaped[1], cell), shaped[2], shaped[3], shaped[4], shaped[5]]
        )

    table = Table(
        data,
        colWidths=[1 * cm, 7 * cm, 2.6 * cm, 2.4 * cm, 1.8 * cm, 3 * cm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563EB")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, -1), _FONT_NAME),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D1D5DB")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F3F4F6")]),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return buffer.getvalue()
