"""Simple invoice PDF rendering with ReportLab."""
from io import BytesIO

from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _money(value):
    return f"${value:,.2f}"


def render_invoice_pdf(invoice):
    """Return the invoice as PDF bytes."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
        topMargin=20 * mm, bottomMargin=20 * mm, title=f"Invoice {invoice.invoice_number}",
    )
    styles = getSampleStyleSheet()
    title = ParagraphStyle("title", parent=styles["Title"], alignment=0, fontSize=22)
    appointment = invoice.appointment
    patient = appointment.patient

    story = [
        Paragraph(settings.CLINIC_NAME, title),
        Paragraph(f"{settings.CLINIC_ADDRESS}<br/>{settings.CLINIC_PHONE}", styles["Normal"]),
        Spacer(1, 10 * mm),
        Paragraph(f"INVOICE {invoice.invoice_number}", styles["Heading2"]),
        Paragraph(
            f"Issued: {invoice.issue_date:%d %b %Y}<br/>Status: {invoice.get_status_display()}",
            styles["Normal"],
        ),
        Spacer(1, 6 * mm),
        Paragraph("<b>Billed to</b>", styles["Normal"]),
        Paragraph(f"{patient.full_name}<br/>{patient.phone}<br/>{patient.email}", styles["Normal"]),
        Spacer(1, 8 * mm),
    ]

    items = Table(
        [
            ["Service", "Date", "Dentist", "Amount"],
            [
                appointment.service.name,
                f"{appointment.date:%d %b %Y}",
                str(appointment.dentist),
                _money(invoice.amount),
            ],
        ],
        colWidths=[65 * mm, 30 * mm, 45 * mm, 30 * mm],
    )
    items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0d6efd")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))
    story += [items, Spacer(1, 6 * mm)]

    payments = list(invoice.payments.all())
    if payments:
        rows = [["Payment date", "Method", "Reference", "Amount"]] + [
            [f"{p.paid_at:%d %b %Y}", p.get_method_display(), p.reference or "-", _money(p.amount)]
            for p in payments
        ]
        table = Table(rows, colWidths=[40 * mm, 40 * mm, 60 * mm, 30 * mm])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
            ("BACKGROUND", (0, 0), (-1, 0), colors.whitesmoke),
            ("ALIGN", (3, 0), (3, -1), "RIGHT"),
        ]))
        story += [Paragraph("<b>Payments</b>", styles["Normal"]), Spacer(1, 2 * mm), table, Spacer(1, 6 * mm)]

    totals = Table(
        [
            ["Total", _money(invoice.amount)],
            ["Paid", _money(invoice.amount_paid)],
            ["Balance due", _money(invoice.balance)],
        ],
        colWidths=[40 * mm, 30 * mm], hAlign="RIGHT",
    )
    totals.setStyle(TableStyle([
        ("ALIGN", (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
        ("LINEABOVE", (0, 2), (-1, 2), 0.8, colors.black),
    ]))
    story.append(totals)

    doc.build(story)
    return buffer.getvalue()
