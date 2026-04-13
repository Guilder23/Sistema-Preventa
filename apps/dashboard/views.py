from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone
from collections import defaultdict
from decimal import Decimal


@login_required
def dashboard(request):
    from apps.clientes.models import Cliente
    from apps.pedidos.models import DetallePedido, DevolucionItem, DevolucionPedido, Pedido
    from apps.productos.models import Producto

    user = request.user
    perfil = getattr(user, "perfil", None)

    # Productos: todos visibles
    total_productos = Producto.objects.filter(activo=True).count()
    costo_inventario_total = sum(
        (
            (producto.stock_unidades or 0) * (producto.precio_compra_unidad or Decimal("0.00"))
            for producto in Producto.objects.filter(activo=True).only("stock_unidades", "precio_compra_unidad")
        ),
        Decimal("0.00"),
    )
    total_usuarios = User.objects.filter(is_active=True).count()

    # Clientes: admin ve todos; preventista solo los suyos
    clientes_qs = Cliente.objects.filter(activo=True)
    if not user.is_superuser and perfil and perfil.rol == "preventista":
        clientes_qs = clientes_qs.filter(creado_por=user)
    total_clientes = clientes_qs.count()

    # Pedidos: admin ve todos; preventista solo los suyos
    pedidos_qs = Pedido.objects.all()
    if not user.is_superuser and perfil and perfil.rol == "preventista":
        pedidos_qs = pedidos_qs.filter(preventista=user)
    total_pedidos = pedidos_qs.count()

    hoy = timezone.localdate()
    pedidos_hoy_qs = pedidos_qs.filter(fecha__date=hoy)
    pedidos_hoy = pedidos_hoy_qs.count()
    pendientes_hoy = pedidos_hoy_qs.filter(estado=Pedido.ESTADO_PENDIENTE).count()
    anulados_hoy = pedidos_hoy_qs.filter(estado=Pedido.ESTADO_ANULADO).count()
    no_entregados_hoy = pedidos_hoy_qs.filter(estado=Pedido.ESTADO_NO_ENTREGADO).count()

    vendidos_hoy_qs = pedidos_qs.filter(
        estado=Pedido.ESTADO_VENDIDO,
        fecha_vendido__date=hoy,
    )
    vendidos_hoy = vendidos_hoy_qs.count()
    monto_vendido_hoy = vendidos_hoy_qs.aggregate(total=Sum("total")).get("total") or 0

    total_vendidos = pedidos_qs.filter(estado=Pedido.ESTADO_VENDIDO).count()
    total_pendientes = pedidos_qs.filter(estado=Pedido.ESTADO_PENDIENTE).count()
    total_anulados = pedidos_qs.filter(estado=Pedido.ESTADO_ANULADO).count()
    total_no_entregados = pedidos_qs.filter(estado=Pedido.ESTADO_NO_ENTREGADO).count()
    total_monto = pedidos_qs.aggregate(total=Sum("total")).get("total") or 0

    pedido_ids = list(pedidos_qs.values_list("id", flat=True))
    monto_devuelto_por_pedido = defaultdict(lambda: Decimal("0.00"))
    und_devueltas_por_pedido = defaultdict(int)
    devolucion_reciente_por_pedido = {}
    costo_vendido_total = Decimal("0.00")
    total_bruto_vendido = Decimal("0.00")

    if pedido_ids:
        devolucion_items = DevolucionItem.objects.filter(
            devolucion__pedido_id__in=pedido_ids,
            detalle_pedido__isnull=False,
        ).select_related("detalle_pedido__producto", "devolucion")

        for it in devolucion_items:
            precio = it.detalle_pedido.precio_unitario if it.detalle_pedido else Decimal("0.00")
            monto_devuelto_por_pedido[it.devolucion.pedido_id] += (precio or Decimal("0.00")) * Decimal(int(it.cantidad_devuelta or 0))
            if it.detalle_pedido_id:
                und_devueltas_por_pedido[it.detalle_pedido_id] += int(it.cantidad_devuelta or 0)

        devoluciones = (
            DevolucionPedido.objects.filter(pedido_id__in=pedido_ids)
            .select_related("repartidor")
            .order_by("pedido_id", "-fecha_creacion")
        )
        for d in devoluciones:
            if d.pedido_id not in devolucion_reciente_por_pedido:
                devolucion_reciente_por_pedido[d.pedido_id] = d

        pedidos_vendidos_qs = pedidos_qs.filter(estado=Pedido.ESTADO_VENDIDO)
        total_bruto_vendido = pedidos_vendidos_qs.aggregate(total=Sum("total")).get("total") or Decimal("0.00")

        detalles_vendidos = (
            DetallePedido.objects.filter(pedido_id__in=pedidos_vendidos_qs.values_list("id", flat=True))
            .select_related("pedido", "producto")
        )
        for detalle in detalles_vendidos:
            devueltas = int(und_devueltas_por_pedido.get(detalle.id, 0))
            cantidad_vendida = max(int(detalle.cantidad or 0) - devueltas, 0)
            costo_vendido_total += Decimal(cantidad_vendida) * (detalle.producto.precio_compra_unidad or Decimal("0.00"))

    total_devuelto_monto = sum(monto_devuelto_por_pedido.values(), Decimal("0.00"))
    total_real_vendido = total_bruto_vendido - total_devuelto_monto
    ganancia_real_total = total_real_vendido - costo_vendido_total

    vendidos_hoy_ids = list(vendidos_hoy_qs.values_list("id", flat=True))
    devuelto_hoy_en_vendidos = sum((monto_devuelto_por_pedido.get(pid, Decimal("0.00")) for pid in vendidos_hoy_ids), Decimal("0.00"))
    ventas_netas_hoy = (monto_vendido_hoy or Decimal("0.00")) - devuelto_hoy_en_vendidos

    costo_vendido_hoy = Decimal("0.00")
    if vendidos_hoy_ids:
        detalles_hoy = DetallePedido.objects.filter(pedido_id__in=vendidos_hoy_ids).select_related("pedido", "producto")
        for detalle in detalles_hoy:
            devueltas = int(und_devueltas_por_pedido.get(detalle.id, 0))
            cantidad_vendida = max(int(detalle.cantidad or 0) - devueltas, 0)
            costo_vendido_hoy += Decimal(cantidad_vendida) * (detalle.producto.precio_compra_unidad or Decimal("0.00"))

    ganancia_real_hoy = ventas_netas_hoy - costo_vendido_hoy

    devoluciones_qs = DevolucionPedido.objects.filter(pedido_id__in=pedido_ids)
    entregas_parciales_total = devoluciones_qs.filter(tipo=DevolucionPedido.TIPO_PARCIAL).values("pedido_id").distinct().count()
    entregas_parciales_hoy = devoluciones_qs.filter(tipo=DevolucionPedido.TIPO_PARCIAL, fecha_creacion__date=hoy).values("pedido_id").distinct().count()

    pedidos_recientes = list(
        pedidos_qs.select_related("cliente", "cliente__creado_por", "preventista", "registrado_por")
        .order_by("-fecha")[:10]
    )

    for p in pedidos_recientes:
        p.total_real = (p.total or Decimal("0.00")) - monto_devuelto_por_pedido.get(p.id, Decimal("0.00"))
        p.devueltos_unidades = und_devueltas_por_pedido.get(p.id, 0)

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

        devol = devolucion_reciente_por_pedido.get(p.id)
        p.repartidor_nombre = (
            (devol.repartidor.get_full_name() or devol.repartidor.username)
            if devol and devol.repartidor
            else "-"
        )

        if p.estado == Pedido.ESTADO_NO_ENTREGADO:
            p.estado_entrega = "No entregado"
        elif p.estado == Pedido.ESTADO_VENDIDO and devol and devol.tipo == DevolucionPedido.TIPO_PARCIAL:
            p.estado_entrega = "Entregado parcial"
        elif p.estado == Pedido.ESTADO_VENDIDO:
            p.estado_entrega = "Entregado completo"
        elif p.estado == Pedido.ESTADO_PENDIENTE:
            p.estado_entrega = "Pendiente"
        else:
            p.estado_entrega = "-"

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "total_productos": total_productos,
            "total_clientes": total_clientes,
            "total_usuarios": total_usuarios,
            "total_pedidos": total_pedidos,
            "total_vendidos": total_vendidos,
            "total_pendientes": total_pendientes,
            "total_anulados": total_anulados,
            "total_monto": total_monto,
            "costo_inventario_total": costo_inventario_total,
            "pedidos_hoy": pedidos_hoy,
            "pendientes_hoy": pendientes_hoy,
            "anulados_hoy": anulados_hoy,
            "no_entregados_hoy": no_entregados_hoy,
            "vendidos_hoy": vendidos_hoy,
            "monto_vendido_hoy": monto_vendido_hoy,
            "ventas_netas_hoy": ventas_netas_hoy,
            "ganancia_real_hoy": ganancia_real_hoy,
            "total_bruto_vendido": total_bruto_vendido,
            "total_devuelto_monto": total_devuelto_monto,
            "total_real_vendido": total_real_vendido,
            "ganancia_real_total": ganancia_real_total,
            "total_no_entregados": total_no_entregados,
            "entregas_parciales_total": entregas_parciales_total,
            "entregas_parciales_hoy": entregas_parciales_hoy,
            "pedidos_recientes": pedidos_recientes,
        },
    )


@login_required
def ayuda(request):
    return render(request, "dashboard/ayuda.html")


@login_required
def configuracion(request):
    return render(request, "dashboard/configuracion.html")
