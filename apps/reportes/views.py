from __future__ import annotations

from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@login_required
def reportes_inicio(request):
    return render(request, "reportes/reportes.html")


def _pedido_qs_para_usuario(user):
    from apps.pedidos.models import Pedido
    from apps.usuarios.models import PerfilUsuario

    perfil = getattr(user, "perfil", None)
    qs = Pedido.objects.select_related("cliente", "preventista")
    if user.is_superuser:
        return qs
    if perfil and perfil.rol == "administrador":
        return qs
    if perfil and perfil.rol == "supervisor":
        preventistas_ids = PerfilUsuario.objects.filter(
            rol="preventista",
            supervisor=user,
            activo=True,
            usuario__is_active=True,
        ).values_list("usuario_id", flat=True)
        return qs.filter(Q(preventista=user) | Q(preventista_id__in=preventistas_ids))
    return qs.filter(preventista=user)


@login_required
def pedido_pdf(request, id: int):
    from apps.pedidos.models import Pedido

    pedido = get_object_or_404(_pedido_qs_para_usuario(request.user), id=id)
    detalles = pedido.detalles.select_related("producto").all()

    def _fmt_money(value) -> str:
        try:
            return f"S/ {value:.2f}"
        except Exception:
            return f"S/ {value}"

    def _draw_header_footer(canvas, doc):
        canvas.saveState()

        page_width, page_height = A4
        accent = colors.HexColor("#d7262b")
        header_dark = colors.HexColor("#d7262b")
        header_accent = colors.HexColor("#332a2a")

        # Footer bar
        footer_h = 14 * mm
        canvas.setFillColor(accent)
        canvas.rect(0, 0, page_width, footer_h, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(16 * mm, 5 * mm, "Sistema Preventa")
        canvas.drawRightString(page_width - 16 * mm, 5 * mm, f"Pedido #{pedido.id}")

        # Header band (dark) + accent shape
        header_h = 22 * mm
        header_y = page_height - header_h
        canvas.setFillColor(header_dark)
        canvas.rect(0, header_y, page_width, header_h, stroke=0, fill=1)

        canvas.setFillColor(header_accent)
        canvas.setStrokeColor(header_accent)
        path = canvas.beginPath()
        x1 = 78 * mm
        x2 = 120 * mm
        y1 = header_y - 2 * mm
        y2 = header_y + 6 * mm
        path.moveTo(x1, y1)
        path.lineTo(x2, y1)
        path.lineTo(x2 + 12 * mm, y2)
        path.lineTo(x1 + 12 * mm, y2)
        path.close()
        canvas.drawPath(path, stroke=0, fill=1)

        canvas.restoreState()

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        title=f"Pedido {pedido.id}",
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=28 * mm,
        bottomMargin=22 * mm,
    )
    styles = getSampleStyleSheet()

    accent = colors.HexColor("#d7262b")
    text_grey = colors.HexColor("#333333")
    muted = colors.HexColor("#6c757d")
    header_bg = colors.HexColor("#e9ecef")
    zebra = colors.HexColor("#f8f9fa")

    title_style = ParagraphStyle(
        "invoice_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        textColor=accent,
        spaceAfter=2,
    )
    label_style = ParagraphStyle(
        "label",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=muted,
        leading=12,
    )
    value_style = ParagraphStyle(
        "value",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=text_grey,
        leading=13,
    )
    small_style = ParagraphStyle(
        "small",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=muted,
        leading=11,
    )

    story = []
    cliente_nombre = f"{pedido.cliente.nombres} {pedido.cliente.apellidos or ''}".strip()
    preventista_nombre = pedido.preventista.get_full_name() or pedido.preventista.username

    # Header block (logo + company + pedido meta)
    logo_path = settings.BASE_DIR / "static" / "img" / "logoAlmacen.png"
    logo_flowable = None
    if logo_path.exists():
        logo_flowable = Image(str(logo_path), width=24 * mm, height=24 * mm)

    left_header = [
        logo_flowable or "",
        Paragraph("<b>Distribuidora JEREMY</b>", value_style),
        Paragraph("Pedidos y preventa", small_style),
    ]

    fecha_venta = pedido.fecha_vendido.strftime("%d/%m/%Y %H:%M") if pedido.fecha_vendido else "--"
    right_header = [
        Paragraph("PEDIDO", title_style),
        Spacer(1, 2),
        Paragraph(f"<b>Número:</b> {pedido.id}", value_style),
        Paragraph(f"<b>Fecha pedido:</b> {pedido.fecha.strftime('%d/%m/%Y %H:%M')}", value_style),
        Paragraph(f"<b>Fecha venta:</b> {fecha_venta}", value_style),
        Paragraph(f"<b>Estado:</b> {pedido.get_estado_display()}", value_style),
    ]
    header_table = Table(
        [[left_header, right_header]],
        colWidths=[105 * mm, 75 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
            ]
        ),
    )
    story.append(header_table)
    story.append(Spacer(1, 10))

    # Client / balance block
    cliente_lines = [
        Paragraph("CLIENTE", label_style),
        Paragraph(cliente_nombre, value_style),
    ]
    if pedido.cliente.ci_nit:
        cliente_lines.append(Paragraph(f"CI/NIT: {pedido.cliente.ci_nit}", small_style))
    if pedido.cliente.telefono:
        cliente_lines.append(Paragraph(f"Tel: {pedido.cliente.telefono}", small_style))
    if pedido.cliente.direccion:
        cliente_lines.append(Paragraph(pedido.cliente.direccion, small_style))

    balance_lines = [
        Paragraph("RESUMEN", label_style),
        Table(
            [
                [Paragraph("Total", value_style), Paragraph(_fmt_money(pedido.total), value_style)],
            ],
            colWidths=[35 * mm, 40 * mm],
            style=TableStyle(
                [
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 0),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            ),
        ),
        Spacer(1, 2),
        Paragraph(f"Realizado por: {preventista_nombre}", small_style),
    ]

    info_table = Table(
        [[cliente_lines, balance_lines]],
        colWidths=[105 * mm, 75 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dee2e6")),
                ("INNERPADDING", (0, 0), (-1, -1), 6),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )
    story.append(info_table)
    story.append(Spacer(1, 12))

    # Items table
    data = [["SL", "Descripción", "Precio", "Cant.", "Total"]]
    for idx, d in enumerate(detalles, start=1):
        desc = d.producto.nombre
        if getattr(d.producto, "codigo", None):
            desc = f"{d.producto.codigo} - {desc}"
        data.append(
            [
                str(idx),
                desc,
                _fmt_money(d.precio_unitario),
                str(d.cantidad),
                _fmt_money(d.subtotal),
            ]
        )

    items_table = Table(
        data,
        colWidths=[10 * mm, 95 * mm, 28 * mm, 18 * mm, 29 * mm],
        repeatRows=1,
    )
    items_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
                ("ALIGN", (3, 1), (3, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd4da")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, zebra]),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(items_table)
    story.append(Spacer(1, 10))

    # Totals block (right aligned)
    totals_data = [
        ["Subtotal", _fmt_money(pedido.total)],
        ["TOTAL", _fmt_money(pedido.total)],
    ]
    totals_table = Table(
        totals_data,
        colWidths=[35 * mm, 40 * mm],
        style=TableStyle(
            [
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("TEXTCOLOR", (0, 0), (-1, 0), muted),
                ("LINEABOVE", (0, 1), (-1, 1), 0.7, colors.HexColor("#cfd4da")),
                ("FONTNAME", (0, 1), (-1, 1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 1), (-1, 1), 11),
                ("TEXTCOLOR", (0, 1), (-1, 1), accent),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        ),
    )
    totals_wrap = Table(
        [["", totals_table]],
        colWidths=[105 * mm, 75 * mm],
        style=TableStyle(
            [
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        ),
    )
    story.append(totals_wrap)
    story.append(Spacer(1, 16))

    # Comentario del pedido
    comentario_text = pedido.observacion or "Sin comentarios registrados."
    comentario_title = Paragraph(
        "Comentario del pedido",
        ParagraphStyle(
            "comentario_title",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=accent,
            leading=12,
        ),
    )
    comentario_box = Table(
        [[comentario_title], [Paragraph(comentario_text, small_style)]],
        colWidths=[165 * mm],
        style=TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dee2e6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        ),
    )
    story.append(comentario_box)
    story.append(Spacer(1, 18))

    # Mensaje de agradecimiento (casi al final)
    terms_text = (
        "Gracias por preferirnos. Agradecemos su confianza y sus pedidos. "
        "Por favor revise los productos al momento de la entrega."
    )
    terms_box = Table(
        [[Paragraph(terms_text, small_style)]],
        colWidths=[165 * mm],
        style=TableStyle(
            [
                ("BOX", (0, 0), (-1, -1), 0.9, colors.HexColor("#dee2e6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        ),
    )
    story.append(terms_box)

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f"inline; filename=pedido_{pedido.id}.pdf"
    return resp
