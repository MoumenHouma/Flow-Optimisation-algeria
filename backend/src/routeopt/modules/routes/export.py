"""Route export to PDF and Excel (F5, docs/ARCHITECTURE.md §2.2 export).

Produces a driver-facing sheet: ordered stops with address, order ref, time
window, weight and phone. Excel handles Arabic addresses natively; the PDF uses
Latin fonts (Arabic shaping in PDF is a documented follow-up).
"""

import io
import uuid
from typing import Any

from openpyxl import Workbook
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from routeopt.models.delivery import Delivery
from routeopt.models.route import Route

_HEADERS = ["#", "Adresse", "Commande", "Fenêtre", "Poids (kg)", "Téléphone"]


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
    cell = styles["BodyText"]
    cell.fontSize = 8

    elements = [
        Paragraph("RouteOpt — Feuille de tournée", styles["Title"]),
        Paragraph(
            f"Tournée {str(route.id)[:8]} · {_distance_label(route)} · {len(route.stops)} arrêts",
            styles["Normal"],
        ),
        Spacer(1, 0.5 * cm),
    ]

    data: list[list[Any]] = [_HEADERS]
    for row in _rows(route, deliveries):
        data.append([row[0], Paragraph(row[1], cell), row[2], row[3], row[4], row[5]])

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
