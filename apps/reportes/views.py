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
from django.utils import timezone

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _display_user_name(user):
    if not user:
        return "-"
    return user.get_full_name() or user.username


def _pedido_repartidor_nombre(pedido, devolucion=None):
    if devolucion and getattr(devolucion, "repartidor", None):
        return _display_user_name(devolucion.repartidor)

    preventista = getattr(pedido, "preventista", None)
    perfil = getattr(preventista, "perfil", None) if preventista else None
    repartidor_asignado = getattr(perfil, "repartidor", None) if perfil else None
    return _display_user_name(repartidor_asignado)


@login_required
def _pedidos_filtrados(request, user):
    from apps.pedidos.models import DevolucionPedido, Pedido
    from django.contrib.auth.models import User

    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    desde = (request.GET.get("desde") or "").strip()
    hasta = (request.GET.get("hasta") or "").strip()
    desde_entrega_raw = (request.GET.get("desde_entrega") or "").strip()
    hasta_entrega_raw = (request.GET.get("hasta_entrega") or "").strip()
    tipo = (request.GET.get("tipo") or "general").strip().lower()
    preventista_id_raw = (request.GET.get("preventista") or "").strip()
    repartidor_id_raw = (request.GET.get("repartidor") or "").strip()
    estado_entrega = (request.GET.get("estado_entrega") or "").strip().lower()

    if tipo not in {"general", "despacho", "devoluciones"}:
        tipo = "general"

    # Para despacho, si no se eligió estado, se asume pendiente.
    if tipo == "despacho" and not estado:
        estado = Pedido.ESTADO_PENDIENTE

    pedidos = _pedido_qs_para_usuario(user).select_related(
        "cliente",
        "preventista",
        "preventista__perfil",
        "preventista__perfil__repartidor",
    )
    pedidos_base = pedidos

    # Opciones de preventista dentro del alcance del usuario.
    preventista_ids = pedidos_base.values_list("preventista_id", flat=True).distinct()
    preventistas = User.objects.filter(id__in=preventista_ids).order_by("username")

    # Repartidores para el filtro
    repartidores = User.objects.filter(perfil__rol="repartidor", is_active=True).order_by("username")

    # Registradores (quienes registraron pedidos) para filtro en General
    registrador_ids = pedidos_base.values_list("registrado_por_id", flat=True).distinct()
    registradores = User.objects.filter(id__in=[r for r in registrador_ids if r]).order_by("username")

    if estado not in {
        Pedido.ESTADO_PENDIENTE,
        Pedido.ESTADO_VENDIDO,
        Pedido.ESTADO_ANULADO,
        Pedido.ESTADO_NO_ENTREGADO,
    }:
        estado = ""

    if q:
        pedido_ids_con_repartidor_q = DevolucionPedido.objects.filter(
            Q(repartidor__username__icontains=q)
            | Q(repartidor__first_name__icontains=q)
            | Q(repartidor__last_name__icontains=q)
        ).values_list("pedido_id", flat=True).distinct()
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=q)
            | Q(cliente__apellidos__icontains=q)
            | Q(cliente__ci_nit__icontains=q)
            | Q(preventista__username__icontains=q)
            | Q(preventista__first_name__icontains=q)
            | Q(preventista__last_name__icontains=q)
            | Q(preventista__perfil__repartidor__username__icontains=q)
            | Q(preventista__perfil__repartidor__first_name__icontains=q)
            | Q(preventista__perfil__repartidor__last_name__icontains=q)
            | Q(id__in=pedido_ids_con_repartidor_q)
        ).distinct()

    if estado:
        pedidos = pedidos.filter(estado=estado)

    estados_entrega_validos = {
        "pendiente",
        "entregado_completo",
        "entregado_parcial",
        "no_entregado",
    }
    if estado_entrega not in estados_entrega_validos:
        estado_entrega = ""

    if estado_entrega:
        parcial_ids = DevolucionPedido.objects.filter(
            tipo=DevolucionPedido.TIPO_PARCIAL
        ).values_list("pedido_id", flat=True)

        if estado_entrega == "pendiente":
            pedidos = pedidos.filter(estado=Pedido.ESTADO_PENDIENTE)
        elif estado_entrega == "no_entregado":
            pedidos = pedidos.filter(estado=Pedido.ESTADO_NO_ENTREGADO)
        elif estado_entrega == "entregado_parcial":
            pedidos = pedidos.filter(estado=Pedido.ESTADO_VENDIDO, id__in=parcial_ids)
        elif estado_entrega == "entregado_completo":
            pedidos = pedidos.filter(estado=Pedido.ESTADO_VENDIDO).exclude(id__in=parcial_ids)

    preventista_id = ""
    if preventista_id_raw:
        try:
            preventista_id_int = int(preventista_id_raw)
        except ValueError:
            preventista_id_int = None
        if preventista_id_int is not None:
            pedidos = pedidos.filter(preventista_id=preventista_id_int)
            preventista_id = str(preventista_id_int)

    # Filtrar por repartidor, considerando tanto el asignado al preventista
    # como el que figure en devoluciones para pedidos ya gestionados.
    repartidor_id = ""
    if repartidor_id_raw:
        try:
            repartidor_id_int = int(repartidor_id_raw)
        except ValueError:
            repartidor_id_int = None
        if repartidor_id_int is not None:
            pedido_ids_con_repartidor = DevolucionPedido.objects.filter(
                repartidor_id=repartidor_id_int
            ).values_list("pedido_id", flat=True).distinct()
            pedidos = pedidos.filter(
                Q(preventista__perfil__repartidor_id=repartidor_id_int)
                | Q(id__in=pedido_ids_con_repartidor)
            ).distinct()
            repartidor_id = str(repartidor_id_int)

    fecha_desde = parse_date(desde) if desde else None
    fecha_hasta = parse_date(hasta) if hasta else None
    fecha_desde_entrega = parse_date(desde_entrega_raw) if desde_entrega_raw else None
    fecha_hasta_entrega = parse_date(hasta_entrega_raw) if hasta_entrega_raw else None

    # Filtrado por fechas: si se proporcionan fechas de entrega explícitas, las priorizamos.
    if fecha_desde_entrega:
        pedidos = pedidos.filter(fecha_entrega_estimada__gte=fecha_desde_entrega)
    elif fecha_desde:
        if tipo == 'despacho':
            pedidos = pedidos.filter(fecha_entrega_estimada__gte=fecha_desde)
        else:
            pedidos = pedidos.filter(fecha__date__gte=fecha_desde)

    if fecha_hasta_entrega:
        pedidos = pedidos.filter(fecha_entrega_estimada__lte=fecha_hasta_entrega)
    elif fecha_hasta:
        if tipo == 'despacho':
            pedidos = pedidos.filter(fecha_entrega_estimada__lte=fecha_hasta)
        else:
            pedidos = pedidos.filter(fecha__date__lte=fecha_hasta)

    pedidos = pedidos.order_by("-fecha")

    filtros = {
        "q": q,
        "estado": estado,
        "desde": desde,
        "hasta": hasta,
        "desde_entrega": desde_entrega_raw,
        "hasta_entrega": hasta_entrega_raw,
        "tipo": tipo,
        "preventista": preventista_id,
        "repartidor": repartidor_id,
        "registrador": "",
        "estado_entrega": estado_entrega,
    }
    return pedidos, filtros, preventistas, repartidores, registradores


@login_required
def reportes_inicio(request):
    from apps.pedidos.models import Pedido, DevolucionItem, DevolucionPedido

    pedidos, filtros, preventistas, repartidores, registradores = _pedidos_filtrados(request, request.user)

    # Si el tipo de reporte es "devoluciones", mostramos una vista diferente
    if filtros.get("tipo") == "devoluciones":
        return _reporte_devoluciones_inicio(request, filtros)
    if filtros.get("tipo") == "despacho":
        return _reporte_despacho_inicio(
            request,
            pedidos,
            filtros,
            preventistas,
            repartidores,
            registradores,
        )

    pedidos = pedidos.select_related(
        "cliente__creado_por",
        "preventista",
        "preventista__perfil",
        "preventista__perfil__repartidor",
        "registrado_por",
    )

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

    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

    # Paginación
    page_number = request.GET.get('page', 1)
    paginator = Paginator(pedidos, 10)  # 10 por página, puedes ajustar
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    pedidos_page = page_obj.object_list
    pedido_ids = [p.id for p in pedidos_page]
    devuelto_monto_por_pedido = defaultdict(lambda: Decimal("0.00"))
    devolucion_reciente_por_pedido = {}

    if pedido_ids:
        devolucion_items = DevolucionItem.objects.filter(
            devolucion__pedido_id__in=pedido_ids,
            detalle_pedido__isnull=False,
        ).select_related("detalle_pedido", "devolucion")

        for item in devolucion_items:
            precio = item.detalle_pedido.precio_unitario if item.detalle_pedido else Decimal("0.00")
            monto = (precio or Decimal("0.00")) * Decimal(int(item.cantidad_devuelta or 0))
            devuelto_monto_por_pedido[item.devolucion.pedido_id] += monto

        devoluciones = (
            DevolucionPedido.objects.filter(pedido_id__in=pedido_ids)
            .select_related("repartidor")
            .order_by("pedido_id", "-fecha_creacion")
        )
        for d in devoluciones:
            if d.pedido_id not in devolucion_reciente_por_pedido:
                devolucion_reciente_por_pedido[d.pedido_id] = d

    def _cliente_corto(cliente):
        nombres = (cliente.nombres or "").strip()
        apellidos = (cliente.apellidos or "").strip()
        if not apellidos:
            return nombres
        iniciales = " ".join([f"{parte[0].upper()}." for parte in apellidos.split() if parte])
        return f"{nombres} {iniciales}".strip()

    for p in pedidos_page:
        monto_devuelto = devuelto_monto_por_pedido.get(p.id, Decimal("0.00"))
        p.total_devuelto_monto = monto_devuelto
        p.total_neto = (p.total or Decimal("0.00")) - monto_devuelto
        p.estado_key = p.estado
        p.cliente_corto = _cliente_corto(p.cliente)

        creado_por_cliente = getattr(p.cliente, "creado_por", None)
        p.cliente_registrado_por = (
            (creado_por_cliente.get_full_name() or creado_por_cliente.username)
            if creado_por_cliente
            else "-"
        )

        registrador = getattr(p, "registrado_por", None)
        p.pedido_registrado_por = (
            (registrador.get_full_name() or registrador.username)
            if registrador
            else (p.preventista.get_full_name() or p.preventista.username)
        )
        p.fecha_pedido_display = p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "-"
        p.fecha_vendido_display = p.fecha_vendido.strftime("%d/%m/%Y %H:%M") if p.fecha_vendido else "-"
        p.fecha_entrega_display = p.fecha_entrega_estimada.strftime("%d/%m/%Y") if getattr(p, 'fecha_entrega_estimada', None) else "-"

        devol = devolucion_reciente_por_pedido.get(p.id)
        p.repartidor_nombre = _pedido_repartidor_nombre(p, devol)

        if p.estado == Pedido.ESTADO_NO_ENTREGADO:
            p.estado_entrega = "No entregado"
            p.estado_entrega_key = "no_entregado"
        elif p.estado == Pedido.ESTADO_VENDIDO:
            if devol and devol.tipo == DevolucionPedido.TIPO_PARCIAL:
                p.estado_entrega = "Entregado parcial"
                p.estado_entrega_key = "entregado_parcial"
            else:
                p.estado_entrega = "Entregado completo"
                p.estado_entrega_key = "entregado_completo"
        elif p.estado == Pedido.ESTADO_PENDIENTE:
            p.estado_entrega = "Pendiente"
            p.estado_entrega_key = "pendiente"
        else:
            p.estado_entrega = "-"
            p.estado_entrega_key = "otro"

    return render(
        request,
        "reportes/reportes.html",
        {
            "pedidos": pedidos_page,
            "page_obj": page_obj,
            "paginator": paginator,
            "q": filtros["q"],
            "estado": filtros["estado"],
            "desde": filtros["desde"],
            "hasta": filtros["hasta"],
            "desde_entrega": filtros.get("desde_entrega", ""),
            "hasta_entrega": filtros.get("hasta_entrega", ""),
            "tipo": filtros["tipo"],
            "preventista": filtros["preventista"],
            "repartidor": filtros.get("repartidor", ""),
            "estado_entrega": filtros["estado_entrega"],
            "preventistas": preventistas,
            "repartidores": repartidores,
            "registradores": registradores,
            "registrador": filtros.get("registrador", ""),
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


def _reporte_despacho_inicio(request, pedidos, filtros, preventistas, repartidores, registradores):
    from apps.pedidos.models import DetallePedido, DevolucionPedido, Pedido
    from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator

    pedidos = pedidos.select_related(
        "cliente",
        "preventista",
        "preventista__perfil",
        "preventista__perfil__repartidor",
        "registrado_por",
    )
    total_pedidos = pedidos.count()
    total_monto = pedidos.aggregate(total=Sum("total")).get("total") or Decimal("0.00")
    total_pendientes = pedidos.filter(estado=Pedido.ESTADO_PENDIENTE).count()
    total_no_entregados = pedidos.filter(estado=Pedido.ESTADO_NO_ENTREGADO).count()
    total_entregados = pedidos.filter(estado=Pedido.ESTADO_VENDIDO).count()

    pedido_ids = list(pedidos.values_list("id", flat=True))
    detalles = (
        DetallePedido.objects.select_related("pedido", "pedido__cliente", "pedido__preventista", "producto")
        .filter(pedido_id__in=pedido_ids)
        .order_by("producto__nombre", "pedido_id")
    )

    consolidado = defaultdict(lambda: {"cantidad": 0, "monto": Decimal("0.00"), "clientes": set(), "precio_unitario": Decimal("0.00")})
    detalle_productos = []
    total_unidades = 0

    for d in detalles:
        cantidad = int(d.cantidad or 0)
        subtotal = d.subtotal or Decimal("0.00")
        total_unidades += cantidad

        item = consolidado[d.producto_id]
        item["nombre"] = d.producto.nombre
        item["cantidad"] += cantidad
        item["monto"] += subtotal
        item["clientes"].add(d.pedido.cliente_id)
        item["precio_unitario"] = d.precio_unitario or Decimal("0.00")

        detalle_productos.append(
            {
                "pedido_id": d.pedido_id,
                "cliente_nombre": f"{d.pedido.cliente.nombres} {d.pedido.cliente.apellidos or ''}".strip(),
                "preventista_nombre": d.pedido.preventista.get_full_name() or d.pedido.preventista.username,
                "producto_nombre": d.producto.nombre,
                "cantidad": cantidad,
                "precio_unitario": d.precio_unitario or Decimal("0.00"),
                "subtotal": subtotal,
            }
        )

    lista_consolidado = []
    for _, item in sorted(consolidado.items(), key=lambda kv: kv[1].get("nombre", "")):
        lista_consolidado.append(
            {
                "producto_nombre": item.get("nombre", "-"),
                "cantidad_total": item["cantidad"],
                "clientes_total": len(item["clientes"]),
                "monto_total": item["monto"],
                "precio_unitario": item["precio_unitario"],
            }
        )

    page_number = request.GET.get("page", 1)
    paginator = Paginator(pedidos, 10)
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    pedidos_page = page_obj.object_list
    devolucion_reciente_por_pedido = {}
    pedidos_page_ids = [p.id for p in pedidos_page]
    if pedidos_page_ids:
        devoluciones = (
            DevolucionPedido.objects.filter(pedido_id__in=pedidos_page_ids)
            .select_related("repartidor")
            .order_by("pedido_id", "-fecha_creacion")
        )
        for devolucion in devoluciones:
            if devolucion.pedido_id not in devolucion_reciente_por_pedido:
                devolucion_reciente_por_pedido[devolucion.pedido_id] = devolucion

    def _cliente_corto(cliente):
        nombres = (cliente.nombres or "").strip()
        apellidos = (cliente.apellidos or "").strip()
        if not apellidos:
            return nombres
        iniciales = " ".join([f"{parte[0].upper()}." for parte in apellidos.split() if parte])
        return f"{nombres} {iniciales}".strip()

    for p in pedidos_page:
        p.cliente_corto = _cliente_corto(p.cliente)
        p.preventista_nombre = p.preventista.get_full_name() or p.preventista.username
        p.fecha_entrega_display = p.fecha_entrega_estimada.strftime("%d/%m/%Y") if p.fecha_entrega_estimada else "-"
        p.fecha_pedido_display = p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "-"
        p.fecha_vendido_display = p.fecha_vendido.strftime("%d/%m/%Y %H:%M") if p.fecha_vendido else "-"

        devol = devolucion_reciente_por_pedido.get(p.id)
        p.repartidor_nombre = _pedido_repartidor_nombre(p, devol)

        if p.estado == Pedido.ESTADO_NO_ENTREGADO:
            p.estado_entrega = "No entregado"
            p.estado_entrega_key = "no_entregado"
        elif p.estado == Pedido.ESTADO_VENDIDO:
            if devol and devol.tipo == DevolucionPedido.TIPO_PARCIAL:
                p.estado_entrega = "Entregado parcial"
                p.estado_entrega_key = "entregado_parcial"
            else:
                p.estado_entrega = "Entregado completo"
                p.estado_entrega_key = "entregado_completo"
        elif p.estado == Pedido.ESTADO_PENDIENTE:
            p.estado_entrega = "Pendiente"
            p.estado_entrega_key = "pendiente"
        else:
            p.estado_entrega = "-"
            p.estado_entrega_key = "otro"

    return render(
        request,
        "reportes/reportes_despacho.html",
        {
            "pedidos": pedidos_page,
            "page_obj": page_obj,
            "paginator": paginator,
            "q": filtros["q"],
            "tipo": filtros["tipo"],
            "desde_entrega": filtros.get("desde_entrega", ""),
            "hasta_entrega": filtros.get("hasta_entrega", ""),
            "estado_entrega": filtros["estado_entrega"],
            "repartidor": filtros.get("repartidor", ""),
            "preventista": filtros["preventista"],
            "preventistas": preventistas,
            "repartidores": repartidores,
            "registradores": registradores,
            "total_pedidos": total_pedidos,
            "total_monto": total_monto,
            "total_pendientes": total_pendientes,
            "total_entregados": total_entregados,
            "total_no_entregados": total_no_entregados,
            "total_unidades": total_unidades,
            "consolidado": lista_consolidado,
            "detalle_productos": detalle_productos,
        },
    )


def _reporte_devoluciones_inicio(request, filtros):
    from apps.pedidos.models import DevolucionItem, DevolucionPedido
    from apps.productos.models import Producto
    from django.contrib.auth.models import User

    # Buscamos ítems devueltos en el rango de fecha
    items_qs = DevolucionItem.objects.select_related(
        "devolucion__pedido__cliente",
        "devolucion__pedido__preventista",
        "devolucion__repartidor",
        "producto"
    )

    if filtros["desde"]:
        items_qs = items_qs.filter(devolucion__fecha_creacion__date__gte=filtros["desde"])
    if filtros["hasta"]:
        items_qs = items_qs.filter(devolucion__fecha_creacion__date__lte=filtros["hasta"])
    
    if filtros["q"]:
        items_qs = items_qs.filter(
            Q(devolucion__pedido__cliente__nombres__icontains=filtros["q"]) |
            Q(devolucion__pedido__cliente__apellidos__icontains=filtros["q"]) |
            Q(devolucion__pedido__cliente__ci_nit__icontains=filtros["q"]) |
            Q(devolucion__pedido__preventista__username__icontains=filtros["q"]) |
            Q(devolucion__pedido__preventista__first_name__icontains=filtros["q"]) |
            Q(devolucion__pedido__preventista__last_name__icontains=filtros["q"]) |
            Q(producto__nombre__icontains=filtros["q"]) |
            Q(devolucion__repartidor__username__icontains=filtros["q"]) |
            Q(devolucion__repartidor__first_name__icontains=filtros["q"]) |
            Q(devolucion__repartidor__last_name__icontains=filtros["q"])
        )

    # Solo devoluciones pendientes de recibir (repuesto=False)
    # El administrador recibe lo que el repartidor trajo físicamente.
    # Usualmente esto se filtra por repuesto=False.
    items_pendientes = items_qs.filter(repuesto=False).order_by("-devolucion__fecha_creacion")

    # Consolidado por producto para la recepción física
    consolidado = defaultdict(lambda: {"cantidad": 0, "monto": Decimal("0.00")})
    for it in items_pendientes:
        key = it.producto_id
        consolidado[key]["nombre"] = it.producto.nombre
        consolidado[key]["cantidad"] += it.cantidad_devuelta
        # Intentamos obtener el precio del detalle si existe, sino del producto
        precio = Decimal("0.00")
        if it.detalle_pedido:
            precio = it.detalle_pedido.precio_unitario
        else:
            precio = it.producto.precio_venta or Decimal("0.00")
        consolidado[key]["monto"] += it.cantidad_devuelta * precio

    lista_consolidado = []
    for pid, data in consolidado.items():
        lista_consolidado.append({
            "producto_id": pid,
            "producto_nombre": data["nombre"],
            "cantidad_total": data["cantidad"],
            "monto_total": data["monto"],
        })
    lista_consolidado.sort(key=lambda x: x["producto_nombre"])

    # Totales para las tarjetas
    total_items = items_pendientes.count()
    total_unidades = sum(it.cantidad_devuelta for it in items_pendientes)
    total_monto_dev = sum(c["monto_total"] for c in lista_consolidado)

    # Repartidores para el filtro (podríamos añadirlo si hace falta)
    repartidores = User.objects.filter(perfil__rol="repartidor", is_active=True).order_by("username")

    return render(
        request,
        "reportes/reportes_devoluciones.html",
        {
            "items": items_pendientes,
            "consolidado": lista_consolidado,
            "q": filtros["q"],
            "desde": filtros["desde"],
            "hasta": filtros["hasta"],
            "tipo": filtros["tipo"],
            "total_items": total_items,
            "total_unidades": total_unidades,
            "total_monto_dev": total_monto_dev,
            "repartidores": repartidores,
        }
    )


@login_required
def pedidos_pdf(request):
    from apps.pedidos.models import DetallePedido, DevolucionItem, DevolucionPedido, Pedido

    pedidos, filtros, preventistas, repartidores, registradores = _pedidos_filtrados(request, request.user)

    if filtros.get("tipo") == "devoluciones":
        return _reporte_devoluciones_pdf(request, filtros)

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
        logo_flowable or Spacer(1, 1),
        Paragraph("<b>Distribuidora JEREMY</b>", value_style),
        Paragraph("Reporte de pedidos", small_style),
    ]

    right_header = [
        Paragraph("REPORTE " + filtros["tipo"].upper(), title_style),
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

    if filtros["tipo"] == "despacho":
        filtros_box = [
            Paragraph("FILTROS APLICADOS", label_style),
            Paragraph(f"Buscar: {filtros['q'] or 'Todos'}", value_style),
            Paragraph("Tipo reporte: Despacho", value_style),
            Paragraph(f"Desde entrega: {filtros['desde_entrega'] or '--'}", value_style),
            Paragraph(f"Hasta entrega: {filtros['hasta_entrega'] or '--'}", value_style),
            Paragraph(f"Estado entrega: {filtros['estado_entrega'] or 'Todos'}", value_style),
            Paragraph(f"Repartidor: {filtros['repartidor'] or 'Todos'}", value_style),
        ]
        resumen_box = [
            Paragraph("RESUMEN", label_style),
            Paragraph(f"Total pedidos: {pedidos.count()}", value_style),
            Paragraph(f"Entregados: {total_vendidos}", small_style),
            Paragraph(f"Pendientes: {total_pendientes}", small_style),
            Paragraph(
                f"No entregados: {pedidos.filter(estado=Pedido.ESTADO_NO_ENTREGADO).count()}",
                small_style,
            ),
        ]
    else:
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

    pedidos = pedidos.select_related(
        "cliente__creado_por",
        "preventista",
        "preventista__perfil",
        "preventista__perfil__repartidor",
        "registrado_por",
    )
    pedido_ids = list(pedidos.values_list("id", flat=True))
    devueltos_por_pedido = {}
    monto_devuelto_por_pedido = defaultdict(lambda: Decimal("0.00"))
    devolucion_reciente_por_pedido = {}
    if pedido_ids:
        devueltos_rows = (
            DevolucionItem.objects.filter(devolucion__pedido_id__in=pedido_ids)
            .values("devolucion__pedido_id")
            .annotate(total_devuelto=Sum("cantidad_devuelta"))
        )
        for row in devueltos_rows:
            devueltos_por_pedido[row["devolucion__pedido_id"]] = int(row["total_devuelto"] or 0)

        devolucion_items = DevolucionItem.objects.filter(
            devolucion__pedido_id__in=pedido_ids,
            detalle_pedido__isnull=False,
        ).select_related("detalle_pedido", "devolucion")
        for item in devolucion_items:
            precio = item.detalle_pedido.precio_unitario if item.detalle_pedido else Decimal("0.00")
            monto = (precio or Decimal("0.00")) * Decimal(int(item.cantidad_devuelta or 0))
            monto_devuelto_por_pedido[item.devolucion.pedido_id] += monto

        devoluciones = (
            DevolucionPedido.objects.filter(pedido_id__in=pedido_ids)
            .select_related("repartidor")
            .order_by("pedido_id", "-fecha_creacion")
        )
        for d in devoluciones:
            if d.pedido_id not in devolucion_reciente_por_pedido:
                devolucion_reciente_por_pedido[d.pedido_id] = d

    def _cliente_corto(cliente):
        nombres = (cliente.nombres or "").strip()
        apellidos = (cliente.apellidos or "").strip()
        if not apellidos:
            return nombres
        iniciales = " ".join([f"{parte[0].upper()}." for parte in apellidos.split() if parte])
        return f"{nombres} {iniciales}".strip()

    def _short(text: str, max_len: int) -> str:
        text = (text or "").strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"

    total_monto = 0
    total_monto_neto = Decimal("0.00")
    for p in pedidos:
        total_monto += p.total
        total_neto = (p.total or Decimal("0.00")) - monto_devuelto_por_pedido.get(p.id, Decimal("0.00"))
        total_monto_neto += total_neto

    if filtros["tipo"] == "general":
        data = [["#", "Cliente", "Cli. por", "Ped. por", "Repart.", "F. pedido", "F. entrega", "F. vendido", "Est. ent.", "Dev.", "Bruto", "Real"]]
        for p in pedidos:
            creado_por_cliente = getattr(p.cliente, "creado_por", None)
            cliente_reg_por = (creado_por_cliente.get_full_name() or creado_por_cliente.username) if creado_por_cliente else "-"
            registrador = getattr(p, "registrado_por", None)
            pedido_reg_por = (
                (registrador.get_full_name() or registrador.username)
                if registrador
                else (p.preventista.get_full_name() or p.preventista.username)
            )
            devol = devolucion_reciente_por_pedido.get(p.id)
            repartidor = _pedido_repartidor_nombre(p, devol)

            if p.estado == Pedido.ESTADO_NO_ENTREGADO:
                estado_entrega = "No entregado"
            elif p.estado == Pedido.ESTADO_VENDIDO and devol and devol.tipo == DevolucionPedido.TIPO_PARCIAL:
                estado_entrega = "Entregado parcial"
            elif p.estado == Pedido.ESTADO_VENDIDO:
                estado_entrega = "Entregado completo"
            elif p.estado == Pedido.ESTADO_PENDIENTE:
                estado_entrega = "Pendiente"
            else:
                estado_entrega = "-"

            total_neto_p = (p.total or Decimal("0.00")) - monto_devuelto_por_pedido.get(p.id, Decimal("0.00"))
            data.append(
                [
                    str(p.id),
                    _short(_cliente_corto(p.cliente), 11),
                    _short(cliente_reg_por, 11),
                    _short(pedido_reg_por, 11),
                    _short(repartidor, 10),
                    p.fecha.strftime("%d/%m/%Y %H:%M"),
                    p.fecha_entrega_estimada.strftime("%d/%m/%Y") if getattr(p, 'fecha_entrega_estimada', None) else "-",
                    p.fecha_vendido.strftime("%d/%m/%Y %H:%M") if p.fecha_vendido else "-",
                    _short(estado_entrega, 14),
                    str(devueltos_por_pedido.get(p.id, 0)),
                    _fmt_money(p.total),
                    _fmt_money(total_neto_p),
                ]
            )

        table = Table(
            data,
            colWidths=[6 * mm, 19 * mm, 16 * mm, 16 * mm, 14 * mm, 18 * mm, 18 * mm, 18 * mm, 17 * mm, 7 * mm, 16 * mm, 16 * mm],
            repeatRows=1,
        )
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, 0), 7),
                    ("FONTSIZE", (0, 1), (-1, -1), 6),
                    ("ALIGN", (0, 0), (0, -1), "CENTER"),
                    ("ALIGN", (5, 1), (7, -1), "CENTER"),
                    ("ALIGN", (8, 1), (8, -1), "CENTER"),
                    ("ALIGN", (9, 1), (10, -1), "RIGHT"),
                    ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd4da")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, zebra]),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 2),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                    ("TOPPADDING", (0, 0), (-1, -1), 1),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 1),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 8))

        totals_data = [
            ["Subtotal vendidos", _fmt_money(subtotal_vendidos)],
            ["Subtotal pendientes", _fmt_money(subtotal_pendientes)],
            ["Subtotal anulados", _fmt_money(subtotal_anulados)],
            ["TOTAL BRUTO", _fmt_money(total_monto)],
            ["TOTAL REAL", _fmt_money(total_monto_neto)],
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
                    ("FONTNAME", (0, 3), (-1, 4), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 3), (-1, 4), 10),
                    ("TEXTCOLOR", (0, 3), (-1, 4), accent),
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

        consolidado = defaultdict(lambda: {"cantidad": 0, "monto": Decimal("0.00"), "clientes": set(), "precio_unitario": Decimal("0.00")})
        for d in detalles:
            key = d.producto_id
            item = consolidado[key]
            item["nombre"] = d.producto.nombre
            item["cantidad"] += int(d.cantidad or 0)
            item["monto"] += d.subtotal or Decimal("0.00")
            item["clientes"].add(d.pedido.cliente_id)
            item["precio_unitario"] = d.precio_unitario or Decimal("0.00")

        data_consolidado = [["Producto", "Precio", "Cant. total", "Clientes", "Monto total"]]
        for _, item in sorted(consolidado.items(), key=lambda kv: kv[1].get("nombre", "")):
            data_consolidado.append(
                [
                    item.get("nombre", "-"),
                    _fmt_money(item["precio_unitario"]),
                    str(item["cantidad"]),
                    str(len(item["clientes"])),
                    _fmt_money(item["monto"]),
                ]
            )

        tabla_consolidado = Table(
            data_consolidado,
            colWidths=[70 * mm, 24 * mm, 26 * mm, 26 * mm, 30 * mm],
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
                    ("ALIGN", (1, 1), (1, -1), "RIGHT"),
                    ("ALIGN", (4, 1), (4, -1), "RIGHT"),
                ]
            )
        )
        story.append(tabla_consolidado)

        # story.append(Spacer(1, 10))
        # story.append(Paragraph("DETALLE DE PRODUCTOS POR PEDIDO", label_style))
        # story.append(Spacer(1, 4))
        #
        # data_detalle = [["Pedido", "Cliente", "Preventista", "Producto", "Cant.", "Precio", "Subtotal"]]
        # for d in detalles:
        #     data_detalle.append(
        #         [
        #             f"#{d.pedido_id}",
        #             f"{d.pedido.cliente.nombres} {d.pedido.cliente.apellidos or ''}".strip(),
        #             d.pedido.preventista.get_full_name() or d.pedido.preventista.username,
        #             d.producto.nombre,
        #             str(d.cantidad),
        #             _fmt_money(d.precio_unitario),
        #             _fmt_money(d.subtotal),
        #         ]
        #     )
        #
        # tabla_detalle = Table(
        #     data_detalle,
        #     colWidths=[14 * mm, 34 * mm, 30 * mm, 54 * mm, 14 * mm, 18 * mm, 20 * mm],
        #     repeatRows=1,
        # )
        # tabla_detalle.setStyle(
        #     TableStyle(
        #         [
        #             ("BACKGROUND", (0, 0), (-1, 0), header_bg),
        #             ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        #             ("FONTSIZE", (0, 0), (-1, 0), 8),
        #             ("FONTSIZE", (0, 1), (-1, -1), 7),
        #             ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd4da")),
        #             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, zebra]),
        #             ("ALIGN", (4, 1), (4, -1), "CENTER"),
        #             ("ALIGN", (5, 1), (6, -1), "RIGHT"),
        #             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        #         ]
        #     )
        # )
        # story.append(tabla_detalle)

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = "inline; filename=reporte_pedidos.pdf"
    return resp


@login_required
def pedido_ticket(request, id: int):
    from apps.pedidos.models import Pedido, DevolucionItem

    pedido = get_object_or_404(_pedido_qs_para_usuario(request.user), id=id)
    if pedido.estado not in {Pedido.ESTADO_VENDIDO, Pedido.ESTADO_NO_ENTREGADO}:
        return redirect("listar_pedidos")

    detalles_qs = list(pedido.detalles.select_related("producto").all())
    detalle_ids = [d.id for d in detalles_qs]

    devueltos_por_detalle = defaultdict(int)
    if detalle_ids:
        devueltos_rows = (
            DevolucionItem.objects.filter(
                devolucion__pedido_id=pedido.id,
                detalle_pedido_id__in=detalle_ids,
            )
            .values("detalle_pedido_id")
            .annotate(total_devuelto=Sum("cantidad_devuelta"))
        )
        for row in devueltos_rows:
            devueltos_por_detalle[row["detalle_pedido_id"]] = int(row["total_devuelto"] or 0)

    detalles = []
    total_devuelto_unidades = 0
    total_devuelto_monto = Decimal("0.00")
    for d in detalles_qs:
        cant_devuelta = int(devueltos_por_detalle.get(d.id, 0))
        subtotal_bruto = d.subtotal or Decimal("0.00")
        monto_devuelto_item = (d.precio_unitario or Decimal("0.00")) * Decimal(cant_devuelta)
        subtotal_neto = subtotal_bruto - monto_devuelto_item

        total_devuelto_unidades += cant_devuelta
        total_devuelto_monto += monto_devuelto_item

        detalles.append(
            {
                "producto_nombre": d.producto.nombre,
                "cantidad": int(d.cantidad or 0),
                "precio_unitario": d.precio_unitario or Decimal("0.00"),
                "cantidad_devuelta": cant_devuelta,
                "subtotal_bruto": subtotal_bruto,
                "subtotal_neto": subtotal_neto,
            }
        )

    total_bruto = pedido.total or Decimal("0.00")
    total_real = total_bruto - total_devuelto_monto

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
            "total_bruto": total_bruto,
            "total_devuelto_unidades": total_devuelto_unidades,
            "total_devuelto_monto": total_devuelto_monto,
            "total_real": total_real,
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
        preventistas_ids = PerfilUsuario.objects.filter(
            rol="preventista",
            repartidor=user,
            activo=True,
            usuario__is_active=True,
        ).values_list("usuario_id", flat=True)
        return qs.filter(
            preventista_id__in=preventistas_ids,
            estado__in=[Pedido.ESTADO_PENDIENTE, Pedido.ESTADO_VENDIDO, Pedido.ESTADO_NO_ENTREGADO]
        )
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
    if not (request.user.is_superuser or (perfil and perfil.rol in {"repartidor", "administrador"})):
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
    from apps.pedidos.models import Pedido, DevolucionItem

    perfil = getattr(request.user, "perfil", None)
    if not (request.user.is_superuser or (perfil and perfil.rol in {"repartidor", "administrador"})):
        return redirect("listar_pedidos")

    pedido = get_object_or_404(_pedido_qs_para_usuario(request.user), id=id)
    if pedido.estado not in {Pedido.ESTADO_VENDIDO, Pedido.ESTADO_NO_ENTREGADO}:
        return redirect("listar_pedidos")

    if not pedido.ticket_compartido:
        pedido.ticket_compartido = True
        pedido.save(update_fields=["ticket_compartido"])

    cliente_nombre = f"{pedido.cliente.nombres} {pedido.cliente.apellidos or ''}".strip()
    ticket_url = request.build_absolute_uri(reverse("reporte_pedido_ticket", args=[pedido.id]))

    detalle_ids = list(pedido.detalles.values_list("id", flat=True))
    total_devuelto_monto = Decimal("0.00")
    if detalle_ids:
        devolucion_items = DevolucionItem.objects.filter(
            devolucion__pedido_id=pedido.id,
            detalle_pedido_id__in=detalle_ids,
        ).select_related("detalle_pedido")
        for item in devolucion_items:
            precio = item.detalle_pedido.precio_unitario if item.detalle_pedido else Decimal("0.00")
            total_devuelto_monto += (precio or Decimal("0.00")) * Decimal(int(item.cantidad_devuelta or 0))

    total_real = (pedido.total or Decimal("0.00")) - total_devuelto_monto

    mensaje = (
        f"Comprobante de entrega\n"
        f"Pedido #{pedido.id}\n"
        f"Cliente: {cliente_nombre}\n"
        f"Estado: {pedido.get_estado_display()}\n"
        f"Total bruto: Bs {(pedido.total or Decimal('0.00')):.2f}\n"
        f"Total real: Bs {total_real:.2f}\n"
        f"Ticket: {ticket_url}"
    )

    return redirect(f"https://wa.me/?text={quote(mensaje)}")


@login_required
def pedido_pdf(request, id: int):
    from apps.pedidos.models import Pedido, DevolucionItem

    pedido = get_object_or_404(_pedido_qs_para_usuario(request.user), id=id)
    detalles = pedido.detalles.select_related("producto").all()

    detalle_ids = list(detalles.values_list("id", flat=True))
    devueltos_por_detalle = {}
    if detalle_ids:
        devueltos_rows = (
            DevolucionItem.objects.filter(
                devolucion__pedido_id=pedido.id,
                detalle_pedido_id__in=detalle_ids,
            )
            .values("detalle_pedido_id")
            .annotate(total_devuelto=Sum("cantidad_devuelta"))
        )
        for row in devueltos_rows:
            devueltos_por_detalle[row["detalle_pedido_id"]] = int(row["total_devuelto"] or 0)

    total_devueltos = sum(devueltos_por_detalle.values())
    total_devuelto_monto = Decimal("0.00")

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
        logo_flowable or Spacer(1, 1),
        Paragraph("<b>Distribuidora JEREMY</b>", value_style),
        Paragraph("Pedidos y preventa", small_style),
    ]

    fecha_venta = pedido.fecha_vendido.strftime("%d/%m/%Y %H:%M") if pedido.fecha_vendido else "--"
    right_header = [
        Paragraph("PEDIDO", title_style),
        Spacer(1, 2),
        Paragraph(f"<b>Número:</b> {pedido.id}", value_style),
        Paragraph(f"<b>Fecha pedido:</b> {pedido.fecha.strftime('%d/%m/%Y %H:%M')}", value_style),
        Paragraph(f"<b>Entrega estimada:</b> {pedido.fecha_entrega_estimada.strftime('%d/%m/%Y')}", value_style) if pedido.fecha_entrega_estimada else Spacer(1, 1),
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
    data = [["SL", "Descripción", "Precio", "Cant.", "Devueltos", "Total bruto", "Total real"]]
    for idx, d in enumerate(detalles, start=1):
        desc = d.producto.nombre
        if getattr(d.producto, "codigo", None):
            desc = f"{d.producto.codigo} - {desc}"
        cant_devuelta = int(devueltos_por_detalle.get(d.id, 0))
        subtotal_neto = (d.subtotal or Decimal("0.00")) - ((d.precio_unitario or Decimal("0.00")) * Decimal(cant_devuelta))
        total_devuelto_monto += (d.precio_unitario or Decimal("0.00")) * Decimal(cant_devuelta)
        data.append(
            [
                str(idx),
                desc,
                _fmt_money(d.precio_unitario),
                str(d.cantidad),
                str(cant_devuelta),
                _fmt_money(d.subtotal),
                _fmt_money(subtotal_neto),
            ]
        )

    total_neto = (pedido.total or Decimal("0.00")) - total_devuelto_monto

    items_table = Table(
        data,
        colWidths=[8 * mm, 66 * mm, 20 * mm, 14 * mm, 14 * mm, 24 * mm, 24 * mm],
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
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("ALIGN", (5, 1), (6, -1), "RIGHT"),
                ("ALIGN", (3, 1), (4, -1), "CENTER"),
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
        ["Devueltos (unid.)", str(total_devueltos)],
        ["Monto devuelto", _fmt_money(total_devuelto_monto)],
        ["Subtotal bruto", _fmt_money(pedido.total)],
        ["TOTAL REAL", _fmt_money(total_neto)],
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
                ("FONTSIZE", (0, 3), (-1, 3), 11),
                ("TEXTCOLOR", (0, 3), (-1, 3), accent),
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


def _reporte_devoluciones_pdf(request, filtros):
    from apps.pedidos.models import DevolucionItem

    # Lógica de filtrado (igual que en la vista)
    items_qs = DevolucionItem.objects.select_related(
        "devolucion__pedido__cliente",
        "devolucion__repartidor",
        "producto",
        "detalle_pedido",
    )

    if filtros["desde"]:
        items_qs = items_qs.filter(devolucion__fecha_creacion__date__gte=filtros["desde"])
    if filtros["hasta"]:
        items_qs = items_qs.filter(devolucion__fecha_creacion__date__lte=filtros["hasta"])

    if filtros["q"]:
        items_qs = items_qs.filter(
            Q(devolucion__pedido__cliente__nombres__icontains=filtros["q"]) |
            Q(devolucion__pedido__cliente__apellidos__icontains=filtros["q"]) |
            Q(producto__nombre__icontains=filtros["q"]) |
            Q(devolucion__repartidor__username__icontains=filtros["q"])
        )

    items_pendientes = items_qs.filter(repuesto=False).order_by("-devolucion__fecha_creacion")

    # Consolidado por producto
    consolidado = defaultdict(lambda: {"cantidad": 0, "monto": Decimal("0.00")})
    for it in items_pendientes:
        key = it.producto_id
        consolidado[key]["nombre"] = it.producto.nombre
        consolidado[key]["cantidad"] += int(it.cantidad_devuelta or 0)
        precio = (
            it.detalle_pedido.precio_unitario
            if it.detalle_pedido
            else (getattr(it.producto, "precio_venta", None) or Decimal("0.00"))
        )
        consolidado[key]["monto"] += Decimal(int(it.cantidad_devuelta or 0)) * (precio or Decimal("0.00"))

    def _short(text: str, max_len: int) -> str:
        text = (text or "").strip()
        if len(text) <= max_len:
            return text
        return text[: max_len - 1] + "…"

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
        canvas.drawRightString(page_width - 16 * mm, 5 * mm, "Reporte de devoluciones")

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
        title="Reporte de devoluciones",
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
        "reporte_title_devol",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=18,
        textColor=accent,
        spaceAfter=2,
    )
    label_style = ParagraphStyle(
        "label_devol",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=9,
        textColor=muted,
        leading=12,
    )
    value_style = ParagraphStyle(
        "value_devol",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=10,
        textColor=text_grey,
        leading=13,
    )
    small_style = ParagraphStyle(
        "small_devol",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        textColor=muted,
        leading=11,
    )

    story = []

    logo_path = settings.BASE_DIR / "static" / "img" / "logoAlmacen.png"
    logo_flowable = None
    if logo_path.exists():
        logo_flowable = Image(str(logo_path), width=24 * mm, height=24 * mm)

    left_header = [
        logo_flowable or Spacer(1, 1),
        Paragraph("<b>Distribuidora JEREMY</b>", value_style),
        Paragraph("Reporte de devoluciones", small_style),
    ]
    right_header = [
        Paragraph("REPORTE", title_style),
        Spacer(1, 2),
        Paragraph("<b>Generado:</b> " + request.user.get_username(), value_style),
        Paragraph("<b>Fecha:</b> " + timezone.now().strftime("%d/%m/%Y %H:%M"), value_style),
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

    total_filas = items_pendientes.count()
    total_unidades = sum(int(it.cantidad_devuelta or 0) for it in items_pendientes)
    total_monto = sum((d["monto"] for d in consolidado.values()), Decimal("0.00"))

    filtros_box = [
        Paragraph("FILTROS APLICADOS", label_style),
        Paragraph(f"Buscar: {filtros['q'] or 'Todos'}", value_style),
        Paragraph("Tipo reporte: Devoluciones físicas", value_style),
        Paragraph(f"Desde: {filtros['desde'] or '--'}", value_style),
        Paragraph(f"Hasta: {filtros['hasta'] or '--'}", value_style),
        Paragraph("Incluye: Solo pendientes de recepción", small_style),
    ]
    resumen_box = [
        Paragraph("RESUMEN", label_style),
        Paragraph(f"Filas devueltas: {total_filas}", value_style),
        Paragraph(f"Total unidades: {total_unidades}", value_style),
        Paragraph(f"Monto estimado: {_fmt_money(total_monto)}", value_style),
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

    # CONSOLIDADO
    story.append(Paragraph("CONSOLIDADO DE PRODUCTOS A RECIBIR", label_style))
    story.append(Spacer(1, 4))

    data_cons = [["Producto", "Cant. total", "Monto est."]]
    for _, d in sorted(consolidado.items(), key=lambda kv: (kv[1].get("nombre") or "").lower()):
        data_cons.append(
            [
                _short(d.get("nombre") or "-", 45),
                str(int(d.get("cantidad") or 0)),
                _fmt_money(d.get("monto") or Decimal("0.00")),
            ]
        )

    tabla_cons = Table(
        data_cons,
        colWidths=[105 * mm, 25 * mm, 40 * mm],
        repeatRows=1,
    )
    tabla_cons.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("FONTSIZE", (0, 1), (-1, -1), 8),
                ("ALIGN", (1, 1), (1, -1), "CENTER"),
                ("ALIGN", (2, 1), (2, -1), "RIGHT"),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd4da")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, zebra]),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(tabla_cons)
    story.append(Spacer(1, 10))

    # DETALLE
    story.append(Paragraph("DETALLE POR PEDIDO Y REPARTIDOR", label_style))
    story.append(Spacer(1, 4))

    data_det = [["Ped#", "Cliente", "Producto", "Cant.", "Repartidor", "Fecha"]]
    for it in items_pendientes:
        cliente = it.devolucion.pedido.cliente
        cliente_nombre = f"{cliente.nombres} {cliente.apellidos or ''}".strip()
        data_det.append(
            [
                f"#{it.devolucion.pedido_id}",
                _short(cliente_nombre, 18),
                _short(it.producto.nombre, 26),
                str(int(it.cantidad_devuelta or 0)),
                _short(it.devolucion.repartidor.get_full_name() or it.devolucion.repartidor.username, 16),
                it.devolucion.fecha_creacion.strftime("%d/%m/%Y"),
            ]
        )

    tabla_det = Table(
        data_det,
        colWidths=[12 * mm, 38 * mm, 55 * mm, 12 * mm, 36 * mm, 25 * mm],
        repeatRows=1,
    )
    tabla_det.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), header_bg),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 8),
                ("FONTSIZE", (0, 1), (-1, -1), 7),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#cfd4da")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, zebra]),
                ("ALIGN", (3, 1), (3, -1), "CENTER"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    story.append(tabla_det)

    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)

    pdf = buffer.getvalue()
    buffer.close()

    resp = HttpResponse(pdf, content_type="application/pdf")
    resp["Content-Disposition"] = "inline; filename=reporte_devoluciones.pdf"
    return resp
