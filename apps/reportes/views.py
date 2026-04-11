from __future__ import annotations

from io import BytesIO

from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


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

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, title=f"Pedido {pedido.id}")
    styles = getSampleStyleSheet()

    story = []
    story.append(Paragraph(f"<b>Pedido #{pedido.id}</b>", styles["Title"]))
    story.append(Spacer(1, 8))

    cliente_nombre = f"{pedido.cliente.nombres} {pedido.cliente.apellidos or ''}".strip()
    preventista_nombre = pedido.preventista.get_full_name() or pedido.preventista.username
    story.append(Paragraph(f"<b>Cliente:</b> {cliente_nombre}", styles["Normal"]))
    story.append(Paragraph(f"<b>Preventista:</b> {preventista_nombre}", styles["Normal"]))
    story.append(Paragraph(f"<b>Fecha:</b> {pedido.fecha.strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Estado:</b> {pedido.get_estado_display()}", styles["Normal"]))
    story.append(Paragraph(f"<b>Total:</b> {pedido.total}", styles["Normal"]))
    if pedido.observacion:
        story.append(Paragraph(f"<b>Obs.:</b> {pedido.observacion}", styles["Normal"]))
    story.append(Spacer(1, 12))

    data = [["Producto", "Precio", "Cant.", "Subtotal"]]
    for d in detalles:
        data.append([
            d.producto.nombre,
            str(d.precio_unitario),
            str(d.cantidad),
            str(d.subtotal),
        ])

    tabla = Table(data, colWidths=[260, 90, 60, 90])
    tabla.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e9ecef")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8f9fa")]),
            ]
        )
    )
    story.append(tabla)

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = f"inline; filename=pedido_{pedido.id}.pdf"
    return resp
