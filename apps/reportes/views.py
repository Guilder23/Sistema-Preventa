from __future__ import annotations

from collections import defaultdict
from decimal import Decimal
from io import BytesIO
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.conf import settings
from django.db.models import Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.dateparse import parse_date

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


@login_required
def _pedidos_filtrados(request, user):
    from apps.pedidos.models import Pedido
    from django.contrib.auth.models import User

    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    desde = (request.GET.get("desde") or "").strip()
    hasta = (request.GET.get("hasta") or "").strip()
    tipo = (request.GET.get("tipo") or "general").strip().lower()
    preventista_id_raw = (request.GET.get("preventista") or "").strip()

    if tipo not in {"general", "despacho"}:
        tipo = "general"

    # Para despacho, si no se eligió estado, se asume pendiente.
    if tipo == "despacho" and not estado:
        estado = Pedido.ESTADO_PENDIENTE

    pedidos = _pedido_qs_para_usuario(user).select_related("cliente", "preventista")
    pedidos_base = pedidos

    # Opciones de preventista dentro del alcance del usuario.
    preventista_ids = pedidos_base.values_list("preventista_id", flat=True).distinct()
    preventistas = User.objects.filter(id__in=preventista_ids).order_by("username")

    if estado not in {Pedido.ESTADO_PENDIENTE, Pedido.ESTADO_VENDIDO, Pedido.ESTADO_ANULADO}:
        estado = ""

    if q:
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=q)
            | Q(cliente__apellidos__icontains=q)
            | Q(cliente__ci_nit__icontains=q)
            | Q(preventista__username__icontains=q)
        )

    if estado:
        pedidos = pedidos.filter(estado=estado)

    preventista_id = ""
    if preventista_id_raw:
        try:
            preventista_id_int = int(preventista_id_raw)
        except ValueError:
            preventista_id_int = None
        if preventista_id_int is not None:
            pedidos = pedidos.filter(preventista_id=preventista_id_int)
            preventista_id = str(preventista_id_int)

    fecha_desde = parse_date(desde) if desde else None
    fecha_hasta = parse_date(hasta) if hasta else None

    if fecha_desde:
        pedidos = pedidos.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        pedidos = pedidos.filter(fecha__date__lte=fecha_hasta)

    pedidos = pedidos.order_by("-fecha")

    filtros = {
        "q": q,
        "estado": estado,
        "desde": desde,
        "hasta": hasta,
        "tipo": tipo,
        "preventista": preventista_id,
    }
    return pedidos, filtros, preventistas


@login_required
def reportes_inicio(request):
    from apps.pedidos.models import Pedido

    pedidos, filtros, preventistas = _pedidos_filtrados(request, request.user)

    resumen = pedidos.aggregate(total_monto=Sum("total"))
    total_pedidos = pedidos.count()
    total_monto = resumen.get("total_monto") or 0
    total_vendidos = pedidos.filter(estado=Pedido.ESTADO_VENDIDO).count()
    total_pendientes = pedidos.filter(estado=Pedido.ESTADO_PENDIENTE).count()
    total_anulados = pedidos.filter(estado=Pedido.ESTADO_ANULADO).count()

    subtotal_vendidos = (
        pedidos.filter(estado=Pedido.ESTADO_VENDIDO).aggregate(total=Sum("total")).get("total")
        or 0
    )
    subtotal_pendientes = (
        pedidos.filter(estado=Pedido.ESTADO_PENDIENTE).aggregate(total=Sum("total")).get("total")
        or 0
    )
    subtotal_anulados = (
        pedidos.filter(estado=Pedido.ESTADO_ANULADO).aggregate(total=Sum("total")).get("total")
        or 0
    )

    return render(
        request,
        "reportes/reportes.html",
        {
            "pedidos": pedidos,
            "q": filtros["q"],
            "estado": filtros["estado"],
            "desde": filtros["desde"],
            "hasta": filtros["hasta"],
            "tipo": filtros["tipo"],
            "preventista": filtros["preventista"],
            "preventistas": preventistas,
            "total_pedidos": total_pedidos,
            "total_monto": total_monto,
            "total_vendidos": total_vendidos,
            "total_pendientes": total_pendientes,
            "total_anulados": total_anulados,
            "subtotal_vendidos": subtotal_vendidos,
            "subtotal_pendientes": subtotal_pendientes,
            "subtotal_anulados": subtotal_anulados,
        },
    )


@login_required
def pedidos_pdf(request):
    from apps.pedidos.models import DetallePedido

    pedidos, filtros, _ = _pedidos_filtrados(request, request.user)

    def _fmt_money(value) -> str:
        try:
            return f"Bs {value:.2f}"
        except Exception:
            return f"Bs {value}"

    def _draw_header_footer(canvas, doc):
        canvas.saveState()

        page_width, page_height = A4
        accent = colors.HexColor("#d7262b")
        header_dark = colors.HexColor("#d7262b")
        header_accent = colors.HexColor("#332a2a")

        footer_h = 14 * mm
        canvas.setFillColor(accent)
        canvas.rect(0, 0, page_width, footer_h, stroke=0, fill=1)
        canvas.setFillColor(colors.white)
        canvas.setFont("Helvetica", 9)
        canvas.drawString(16 * mm, 5 * mm, "Sistema Preventa")
        canvas.drawRightString(page_width - 16 * mm, 5 * mm, "Reporte de pedidos")

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
        title="Reporte de pedidos",
        leftMargin=16 * mm,
        rightMargin=16 * mm,
        topMargin=28 * mm,
        bottomMargin=18 * mm,
    )

    styles = getSampleStyleSheet()

    accent = colors.HexColor("#d7262b")
    text_grey = colors.HexColor("#333333")
    muted = colors.HexColor("#6c757d")
    header_bg = colors.HexColor("#e9ecef")
    zebra = colors.HexColor("#f8f9fa")

    title_style = ParagraphStyle(
        "reporte_title",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
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

    total_vendidos = pedidos.filter(estado="vendido").count()
    total_pendientes = pedidos.filter(estado="pendiente").count()
    total_anulados = pedidos.filter(estado="anulado").count()

    subtotal_vendidos = (
        pedidos.filter(estado="vendido").aggregate(total=Sum("total")).get("total") or 0
    )
    subtotal_pendientes = (
        pedidos.filter(estado="pendiente").aggregate(total=Sum("total")).get("total") or 0
    )
    subtotal_anulados = (
        pedidos.filter(estado="anulado").aggregate(total=Sum("total")).get("total") or 0
    )

    story = []

    logo_path = settings.BASE_DIR / "static" / "img" / "logoAlmacen.png"
    logo_flowable = None
    if logo_path.exists():
        logo_flowable = Image(str(logo_path), width=24 * mm, height=24 * mm)

    left_header = [
        logo_flowable or "",
        Paragraph("<b>Distribuidora JEREMY</b>", value_style),
        Paragraph("Reporte de pedidos", small_style),
    ]

    right_header = [
        Paragraph("REPORTE", title_style),
        Spacer(1, 2),
        Paragraph("<b>Generado:</b> " + request.user.get_username(), value_style),
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

    filtros_box = [
        Paragraph("FILTROS APLICADOS", label_style),
        Paragraph(f"Buscar: {filtros['q'] or 'Todos'}", value_style),
        Paragraph(f"Tipo reporte: {filtros['tipo'].capitalize()}", value_style),
        Paragraph(f"Estado: {filtros['estado'] or 'Todos'}", value_style),
        Paragraph(f"Preventista: {filtros['preventista'] or 'Todos'}", value_style),
        Paragraph(f"Desde: {filtros['desde'] or '--'}", value_style),
        Paragraph(f"Hasta: {filtros['hasta'] or '--'}", value_style),
    ]
    resumen_box = [
        Paragraph("RESUMEN", label_style),
        Paragraph(f"Total pedidos: {pedidos.count()}", value_style),
        Paragraph(f"Vendidos: {total_vendidos}", small_style),
        Paragraph(f"Pendientes: {total_pendientes}", small_style),
        Paragraph(f"Anulados: {total_anulados}", small_style),
    ]

    info_table = Table(
        [[filtros_box, resumen_box]],
        colWidths=[105 * mm, 75 * mm],
        style=TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("BACKGROUND", (0, 0), (-1, -1), colors.white),
                ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#dee2e6")),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        ),
    )
    story.append(info_table)
    story.append(Spacer(1, 12))

    data = [["#", "Cliente", "Preventista", "Fecha", "Estado", "Total"]]
    total_monto = 0
    for p in pedidos:
        total_monto += p.total
        data.append(
            [
                str(p.id),
                f"{p.cliente.nombres} {p.cliente.apellidos or ''}".strip(),
                p.preventista.get_full_name() or p.preventista.username,
                p.fecha.strftime("%d/%m/%Y %H:%M"),
                p.get_estado_display(),
                _fmt_money(p.total),
            ]
        )

    table = Table(
        data,
        colWidths=[12 * mm, 45 * mm, 33 * mm, 38 * mm, 26 * mm, 24 * mm],
        repeatRows=1,
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (-1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd4da")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, zebra]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 8))

    totals_data = [
        ["Subtotal vendidos", _fmt_money(subtotal_vendidos)],
        ["Subtotal pendientes", _fmt_money(subtotal_pendientes)],
        ["Subtotal anulados", _fmt_money(subtotal_anulados)],
        ["TOTAL", _fmt_money(total_monto)],
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
                ("LINEABOVE", (0, 3), (-1, 3), 0.7, colors.HexColor("#cfd4da")),
                ("FONTNAME", (0, 3), (-1, 3), "Helvetica-Bold"),
                ("FONTSIZE", (0, 3), (-1, 3), 10),
                ("TEXTCOLOR", (0, 3), (-1, 3), accent),
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

    # Sección de despacho: consolidado + detalle de productos por pedido.
    if filtros["tipo"] == "despacho" and pedidos.exists():
        story.append(Spacer(1, 12))
        story.append(Paragraph("CONSOLIDADO DE CARGA PARA REPARTO", label_style))
        story.append(Spacer(1, 4))

        pedido_ids = list(pedidos.values_list("id", flat=True))
        detalles = (
            DetallePedido.objects.select_related("pedido", "pedido__cliente", "pedido__preventista", "producto")
            .filter(pedido_id__in=pedido_ids)
            .order_by("producto__nombre", "pedido_id")
        )

        consolidado = defaultdict(lambda: {"cantidad": 0, "monto": Decimal("0.00"), "clientes": set()})
        for d in detalles:
            key = d.producto_id
            item = consolidado[key]
            item["nombre"] = d.producto.nombre
            item["cantidad"] += int(d.cantidad or 0)
            item["monto"] += d.subtotal or Decimal("0.00")
            item["clientes"].add(d.pedido.cliente_id)

        data_consolidado = [["Producto", "Cant. total", "Clientes", "Monto total"]]
        for _, item in sorted(consolidado.items(), key=lambda kv: kv[1].get("nombre", "")):
            data_consolidado.append(
                [
                    item.get("nombre", "-"),
                    str(item["cantidad"]),
                    str(len(item["clientes"])),
                    _fmt_money(item["monto"]),
                ]
            )

        tabla_consolidado = Table(
            data_consolidado,
            colWidths=[84 * mm, 28 * mm, 28 * mm, 36 * mm],
            repeatRows=1,
        )
        tabla_consolidado.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 9),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd4da")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, zebra]),
                    ("ALIGN", (1, 1), (-1, -1), "CENTER"),
                    ("ALIGN", (3, 1), (3, -1), "RIGHT"),
                ]
            )
        )
        story.append(tabla_consolidado)

        story.append(Spacer(1, 10))
        story.append(Paragraph("DETALLE DE PRODUCTOS POR PEDIDO", label_style))
        story.append(Spacer(1, 4))

        data_detalle = [["Pedido", "Cliente", "Preventista", "Producto", "Cant.", "Precio", "Subtotal"]]
        for d in detalles:
            data_detalle.append(
                [
                    f"#{d.pedido_id}",
                    f"{d.pedido.cliente.nombres} {d.pedido.cliente.apellidos or ''}".strip(),
                    d.pedido.preventista.get_full_name() or d.pedido.preventista.username,
                    d.producto.nombre,
                    str(d.cantidad),
                    _fmt_money(d.precio_unitario),
                    _fmt_money(d.subtotal),
                ]
            )

        tabla_detalle = Table(
            data_detalle,
            colWidths=[14 * mm, 34 * mm, 30 * mm, 54 * mm, 14 * mm, 18 * mm, 20 * mm],
            repeatRows=1,
        )
        tabla_detalle.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 8),
                    ("FONTSIZE", (0, 1), (-1, -1), 7),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd4da")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, zebra]),
                    ("ALIGN", (4, 1), (4, -1), "CENTER"),
                    ("ALIGN", (5, 1), (6, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ]
            )
        )
        story.append(tabla_detalle)

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = "inline; filename=reporte_pedidos.pdf"
    return resp


@login_required
def pedido_ticket(request, id: int):
    from apps.pedidos.models import Pedido

    pedido = get_object_or_404(_pedido_qs_para_usuario(request.user), id=id)
    if pedido.estado not in {Pedido.ESTADO_VENDIDO, Pedido.ESTADO_NO_ENTREGADO}:
        return redirect("listar_pedidos")

    detalles = pedido.detalles.select_related("producto").all()

    repartidor = request.user.get_full_name() or request.user.username
    cliente_nombre = f"{pedido.cliente.nombres} {pedido.cliente.apellidos or ''}".strip()
    preventista_nombre = pedido.preventista.get_full_name() or pedido.preventista.username

    return render(
        request,
        "reportes/pedido_ticket.html",
        {
            "pedido": pedido,
            "detalles": detalles,
            "cliente_nombre": cliente_nombre,
            "preventista_nombre": preventista_nombre,
            "repartidor_nombre": repartidor,
            "estado_display": pedido.get_estado_display(),
        },
    )


def _pedido_qs_para_usuario(user):
    from apps.pedidos.models import Pedido
    from apps.usuarios.models import PerfilUsuario

    perfil = getattr(user, "perfil", None)
    qs = Pedido.objects.select_related("cliente", "preventista")
    if user.is_superuser:
        return qs
    if perfil and perfil.rol == "administrador":
        return qs
    if perfil and perfil.rol == "repartidor":
        return qs.filter(estado__in=[Pedido.ESTADO_PENDIENTE, Pedido.ESTADO_VENDIDO, Pedido.ESTADO_NO_ENTREGADO])
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
def marcar_ticket_impreso(request, id: int):
    from apps.pedidos.models import Pedido

    if request.method != "POST":
        return JsonResponse({"ok": False, "error": "Método no permitido"}, status=405)

    perfil = getattr(request.user, "perfil", None)
    if not (request.user.is_superuser or (perfil and perfil.rol == "repartidor")):
        return JsonResponse({"ok": False, "error": "Sin permisos"}, status=403)

    pedido = get_object_or_404(_pedido_qs_para_usuario(request.user), id=id)
    if pedido.estado not in {Pedido.ESTADO_VENDIDO, Pedido.ESTADO_NO_ENTREGADO}:
        return JsonResponse(
            {"ok": False, "error": "El ticket se habilita cuando el pedido está vendido o no entregado"},
            status=400,
        )

    if not pedido.ticket_impreso:
        pedido.ticket_impreso = True
        pedido.save(update_fields=["ticket_impreso"])

    return JsonResponse({"ok": True})


@login_required
def compartir_ticket_whatsapp(request, id: int):
    from apps.pedidos.models import Pedido

    perfil = getattr(request.user, "perfil", None)
    if not (request.user.is_superuser or (perfil and perfil.rol == "repartidor")):
        return redirect("listar_pedidos")

    pedido = get_object_or_404(_pedido_qs_para_usuario(request.user), id=id)
    if pedido.estado not in {Pedido.ESTADO_VENDIDO, Pedido.ESTADO_NO_ENTREGADO}:
        return redirect("listar_pedidos")

    if not pedido.ticket_compartido:
        pedido.ticket_compartido = True
        pedido.save(update_fields=["ticket_compartido"])

    cliente_nombre = f"{pedido.cliente.nombres} {pedido.cliente.apellidos or ''}".strip()
    ticket_url = request.build_absolute_uri(reverse("reporte_pedido_ticket", args=[pedido.id]))

    mensaje = (
        f"Comprobante de entrega\n"
        f"Pedido #{pedido.id}\n"
        f"Cliente: {cliente_nombre}\n"
        f"Estado: {pedido.get_estado_display()}\n"
        f"Total: Bs {pedido.total:.2f}\n"
        f"Ticket: {ticket_url}"
    )

    return redirect(f"https://wa.me/?text={quote(mensaje)}")


@login_required
def pedido_pdf(request, id: int):
    from apps.pedidos.models import Pedido

    pedido = get_object_or_404(_pedido_qs_para_usuario(request.user), id=id)
    detalles = pedido.detalles.select_related("producto").all()

    def _fmt_money(value) -> str:
        try:
            return f"Bs {value:.2f}"
        except Exception:
            return f"Bs {value}"

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
