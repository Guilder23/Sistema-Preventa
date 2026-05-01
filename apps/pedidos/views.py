from __future__ import annotations

from datetime import date
from decimal import Decimal
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q
from django.db.models import F
from django.db.models.functions import Greatest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.usuarios.decorators import role_required
from apps.usuarios.models import PerfilUsuario

from .models import DevolucionItem, DevolucionPedido, DetallePedido, Pedido


def _descontar_stock_por_detalles(detalles):
    for det in detalles:
        Producto.objects.filter(id=det.producto_id).update(
            stock_unidades=Greatest(F("stock_unidades") - det.cantidad, 0)
        )


def _reponer_stock_por_detalles(detalles):
    for det in detalles:
        Producto.objects.filter(id=det.producto_id).update(
            stock_unidades=F("stock_unidades") + det.cantidad
        )


def _reponer_item_devolucion(item: DevolucionItem, user):
    if item.repuesto:
        return False

    Producto.objects.filter(id=item.producto_id).update(
        stock_unidades=F("stock_unidades") + item.cantidad_devuelta
    )
    item.repuesto = True
    item.fecha_reposicion = timezone.now()
    item.repuesto_por = user
    item.save(update_fields=["repuesto", "fecha_reposicion", "repuesto_por"])
    item.devolucion.actualizar_estado_reposicion(save=True)
    return True


def _resumen_reposicion_desde_items(items_qs):
    pendientes_por_producto = defaultdict(int)

    for it in items_qs:
        if it.repuesto:
            continue
        if int(it.cantidad_devuelta or 0) <= 0:
            continue
        pendientes_por_producto[it.producto_id] += int(it.cantidad_devuelta)

    if not pendientes_por_producto:
        return {
            "productos": [],
            "total_items": 0,
            "total_aumenta": 0,
        }

    productos_qs = Producto.objects.filter(id__in=pendientes_por_producto.keys()).values(
        "id", "nombre", "stock_unidades"
    )

    productos = []
    total_aumenta = 0
    for p in productos_qs:
        aumenta = int(pendientes_por_producto.get(p["id"], 0))
        stock_actual = int(p.get("stock_unidades") or 0)
        stock_final = stock_actual + aumenta
        total_aumenta += aumenta
        productos.append(
            {
                "producto": p.get("nombre") or "",
                "stock_actual": stock_actual,
                "aumenta": aumenta,
                "stock_final": stock_final,
            }
        )

    productos.sort(key=lambda x: x["producto"].lower())
    return {
        "productos": productos,
        "total_items": len(productos),
        "total_aumenta": total_aumenta,
    }


def _clientes_para_usuario(user):
    perfil = getattr(user, "perfil", None)
    qs = Cliente.objects.filter(activo=True)
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
        return qs.filter(Q(creado_por=user) | Q(creado_por_id__in=preventistas_ids))
    return qs.filter(creado_por=user)


def _construir_datos_pedidos_form(user):
    clientes = _clientes_para_usuario(user).order_by("nombres", "apellidos")
    productos = Producto.objects.filter(activo=True).order_by("nombre")

    clientes_data = []
    for c in clientes:
        label = f"{c.nombres}{(' ' + c.apellidos) if c.apellidos else ''}{(' - ' + c.ci_nit) if c.ci_nit else ''}"
        clientes_data.append({"id": c.id, "label": label})

    productos_data = []
    for p in productos:
        label = p.nombre
        productos_data.append(
            {
                "id": p.id,
                "label": label,
                "precio": str(p.precio_unidad or Decimal('0.00')),
                "stock": int(getattr(p, 'stock_unidades', 0) or 0),
            }
        )

    return {
        "clientes": clientes,
        "productos": productos,
        "clientes_data": clientes_data,
        "productos_data": productos_data,
    }


def _pedidos_qs_para_usuario(user):
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


@role_required("administrador", "supervisor", "preventista", "repartidor")
def listar_pedidos(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    rol_usuario = (request.GET.get("rol") or "").strip().lower()
    fecha_desde_raw = (request.GET.get("fecha_desde") or "").strip()
    fecha_hasta_raw = (request.GET.get("fecha_hasta") or "").strip()
    vista_pedidos = (request.GET.get("tab") or "pendientes").strip().lower()
    if vista_pedidos not in {"pendientes", "anteriores"}:
        vista_pedidos = "pendientes"

    fecha_desde = None
    fecha_hasta = None
    try:
        if fecha_desde_raw:
            fecha_desde = date.fromisoformat(fecha_desde_raw)
    except ValueError:
        fecha_desde = None
        fecha_desde_raw = ""

    try:
        if fecha_hasta_raw:
            fecha_hasta = date.fromisoformat(fecha_hasta_raw)
    except ValueError:
        fecha_hasta = None
        fecha_hasta_raw = ""

    pedidos = _pedidos_qs_para_usuario(request.user)

    if estado not in {
        Pedido.ESTADO_PENDIENTE,
        Pedido.ESTADO_VENDIDO,
        Pedido.ESTADO_NO_ENTREGADO,
        Pedido.ESTADO_ANULADO,
    }:
        estado = ""

    if q:
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=q)
            | Q(cliente__apellidos__icontains=q)
            | Q(cliente__ci_nit__icontains=q)
        )

    if estado:
        pedidos = pedidos.filter(estado=estado)

    roles_validos = {"administrador", "supervisor", "preventista", "repartidor"}
    if rol_usuario not in roles_validos:
        rol_usuario = ""

    if rol_usuario:
        if rol_usuario == "administrador":
            pedidos = pedidos.filter(
                Q(preventista__is_superuser=True) | Q(preventista__perfil__rol="administrador")
            )
        else:
            pedidos = pedidos.filter(preventista__perfil__rol=rol_usuario)

    if fecha_desde:
        pedidos = pedidos.filter(fecha__date__gte=fecha_desde)
    if fecha_hasta:
        pedidos = pedidos.filter(fecha__date__lte=fecha_hasta)

    if vista_pedidos == "pendientes":
        pedidos = pedidos.filter(estado=Pedido.ESTADO_PENDIENTE)
    else:
        pedidos = pedidos.exclude(estado=Pedido.ESTADO_PENDIENTE)

    pedidos = list(pedidos.order_by("-fecha"))

    pedido_ids = [p.id for p in pedidos]
    devuelto_monto_por_pedido = defaultdict(lambda: Decimal("0.00"))
    if pedido_ids:
        devolucion_items = DevolucionItem.objects.filter(
            devolucion__pedido_id__in=pedido_ids,
            detalle_pedido__isnull=False,
        ).select_related("detalle_pedido", "devolucion")

        for item in devolucion_items:
            precio = item.detalle_pedido.precio_unitario if item.detalle_pedido else Decimal("0.00")
            monto = (precio or Decimal("0.00")) * Decimal(int(item.cantidad_devuelta or 0))
            devuelto_monto_por_pedido[item.devolucion.pedido_id] += monto

    for p in pedidos:
        monto_devuelto = devuelto_monto_por_pedido.get(p.id, Decimal("0.00"))
        p.total_devuelto_monto = monto_devuelto
        p.total_neto = (p.total or Decimal("0.00")) - monto_devuelto
        # Fechas formateadas para la vista
        p.fecha_pedido_display = p.fecha.strftime("%d/%m/%Y %H:%M") if p.fecha else "-"
        p.fecha_entrega_display = p.fecha_entrega_estimada.strftime("%d/%m/%Y") if getattr(p, 'fecha_entrega_estimada', None) else "-"
        p.fecha_vendido_display = p.fecha_vendido.strftime("%d/%m/%Y %H:%M") if getattr(p, 'fecha_vendido', None) else "-"

    perfil = getattr(request.user, "perfil", None)
    if perfil and perfil.rol == "repartidor":
        clientes = Cliente.objects.none()
        productos = Producto.objects.none()
        clientes_data = []
        productos_data = []
    else:
        form_data = _construir_datos_pedidos_form(request.user)
        clientes = form_data['clientes']
        productos = form_data['productos']
        clientes_data = form_data['clientes_data']
        productos_data = form_data['productos_data']

    # PAGINACIÓN
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    page = request.GET.get("page", 1)
    paginator = Paginator(pedidos, 10)  # 10 pedidos por página
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(
        request,
        "pedidos/pedidos.html",
        {
            "pedidos": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "q": q,
            "estado": estado,
            "rol_usuario": rol_usuario,
            "fecha_desde": fecha_desde_raw,
            "fecha_hasta": fecha_hasta_raw,
            "vista_pedidos": vista_pedidos,
            "clientes": clientes,
            "productos": productos,
            "clientes_data": clientes_data,
            "productos_data": productos_data,
        },
    )


@role_required("administrador", "supervisor", "preventista")
def crear_pedido(request):
    from django.utils.dateparse import parse_date

    if request.method == "GET":
        form_data = _construir_datos_pedidos_form(request.user)
        return render(
            request,
            "pedidos/crear.html",
            {
                "clientes": form_data["clientes"],
                "productos": form_data["productos"],
                "clientes_data": form_data["clientes_data"],
                "productos_data": form_data["productos_data"],
            },
        )

    cliente_id = (request.POST.get("cliente_id") or "").strip()
    observacion = (request.POST.get("observacion") or "").strip()
    fecha_entrega_estimada_raw = (request.POST.get("fecha_entrega_estimada") or "").strip()

    producto_ids = request.POST.getlist("producto_id[]")
    cantidades = request.POST.getlist("cantidad[]")

    if not cliente_id:
        messages.error(request, "Selecciona un cliente")
        return redirect("crear_pedido")

    # Validar fecha de entrega estimada
    if not fecha_entrega_estimada_raw:
        messages.error(request, "Ingresa una fecha de entrega estimada")
        return redirect("crear_pedido")
    
    fecha_entrega_estimada = parse_date(fecha_entrega_estimada_raw)
    if not fecha_entrega_estimada:
        messages.error(request, "Formato de fecha inválido")
        return redirect("crear_pedido")
    
    hoy = date.today()
    if fecha_entrega_estimada < hoy:
        messages.error(request, "La fecha de entrega no puede ser menor a hoy")
        return redirect("crear_pedido")

    cliente = get_object_or_404(_clientes_para_usuario(request.user), id=cliente_id)

    items = []
    for pid, cant in zip(producto_ids, cantidades):
        pid = (pid or "").strip()
        cant = (cant or "").strip()
        if not pid or not cant:
            continue
        try:
            cantidad_int = int(cant)
        except ValueError:
            continue
        if cantidad_int <= 0:
            continue
        items.append((pid, cantidad_int))

    if not items:
        messages.error(request, "Agrega al menos un producto con cantidad")
        return redirect("crear_pedido")

    # Consolidar cantidades por producto (evita duplicados que rompan el stock)
    qty_por_pid = {}
    for pid, cantidad_int in items:
        qty_por_pid[pid] = int(qty_por_pid.get(pid, 0)) + int(cantidad_int)

    with transaction.atomic():
        productos = list(
            Producto.objects.select_for_update().filter(id__in=qty_por_pid.keys(), activo=True)
        )
        productos_por_id = {str(p.id): p for p in productos}

        # validar existencia + stock + precio
        for pid, cantidad_int in qty_por_pid.items():
            producto = productos_por_id.get(str(pid))
            if not producto:
                messages.error(request, "Producto inválido")
                return redirect("crear_pedido")
            stock = int(getattr(producto, "stock_unidades", 0) or 0)
            precio = producto.precio_unidad or Decimal("0.00")
            if cantidad_int > stock:
                messages.error(request, f'Stock insuficiente para "{producto.nombre}" (stock: {stock})')
                return redirect("crear_pedido")
            if precio <= 0:
                messages.error(request, f'No puedes vender "{producto.nombre}" porque su precio es 0')
                return redirect("crear_pedido")

        preventista_asignado = cliente.creado_por or request.user
        pedido = Pedido.objects.create(
            cliente=cliente,
            preventista=preventista_asignado,
            registrado_por=request.user,
            observacion=observacion or None,
            fecha_entrega_estimada=fecha_entrega_estimada,
        )

        total = Decimal("0.00")
        detalles_creados = []
        for pid, cantidad_int in qty_por_pid.items():
            producto = productos_por_id.get(str(pid))
            precio = producto.precio_unidad or Decimal("0.00")
            subtotal = (precio * Decimal(cantidad_int)).quantize(Decimal("0.01"))
            det = DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=cantidad_int,
                precio_unitario=precio,
                subtotal=subtotal,
            )
            detalles_creados.append(det)
            total += subtotal

        pedido.total = total.quantize(Decimal("0.01"))
        # Descontar stock al registrar el pedido
        _descontar_stock_por_detalles(detalles_creados)
        pedido.stock_descontado = True
        pedido.save(update_fields=["total", "stock_descontado"])

    messages.success(request, "Pedido creado")
    return redirect("listar_pedidos")


@role_required("administrador", "supervisor", "preventista", "repartidor")
def obtener_pedido(request, id: int):
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    detalles_qs = pedido.detalles.select_related("producto").all()
    detalle_ids = [d.id for d in detalles_qs]

    devueltos_por_detalle = defaultdict(int)
    if detalle_ids:
        devolucion_items = DevolucionItem.objects.filter(
            devolucion__pedido_id=pedido.id,
            detalle_pedido_id__in=detalle_ids,
        )
        for it in devolucion_items:
            devueltos_por_detalle[it.detalle_pedido_id] += int(it.cantidad_devuelta or 0)

    detalles = []
    total_devuelto_monto = Decimal("0.00")
    for d in detalles_qs:
        cant_devuelta = int(devueltos_por_detalle.get(d.id, 0))
        subtotal_neto = (d.subtotal or Decimal("0.00")) - ((d.precio_unitario or Decimal("0.00")) * Decimal(cant_devuelta))
        total_devuelto_monto += (d.precio_unitario or Decimal("0.00")) * Decimal(cant_devuelta)

        detalles.append(
            {
                "id": d.id,
                "producto_id": d.producto_id,
                "producto__nombre": d.producto.nombre,
                "cantidad": d.cantidad,
                "precio_unitario": f"{(d.precio_unitario or Decimal('0.00')):.2f}",
                "subtotal": f"{(d.subtotal or Decimal('0.00')):.2f}",
                "cantidad_devuelta": cant_devuelta,
                "subtotal_neto": f"{subtotal_neto:.2f}",
            }
        )

    total_neto = (pedido.total or Decimal("0.00")) - total_devuelto_monto

    return JsonResponse(
        {
            "id": pedido.id,
            "cliente": f"{pedido.cliente.nombres} {pedido.cliente.apellidos or ''}".strip(),
            "preventista": pedido.preventista.get_full_name() or pedido.preventista.username,
            "fecha": pedido.fecha.strftime("%d/%m/%Y %H:%M"),
            "fecha_entrega_estimada": pedido.fecha_entrega_estimada.isoformat() if pedido.fecha_entrega_estimada else "",
            "fecha_vendido": pedido.fecha_vendido.isoformat() if getattr(pedido, 'fecha_vendido', None) else "",
            "estado": pedido.estado,
            "estado_display": pedido.get_estado_display(),
            "total": f"{(pedido.total or Decimal('0.00')):.2f}",
            "total_devuelto_monto": f"{total_devuelto_monto:.2f}",
            "total_neto": f"{total_neto:.2f}",
            "observacion": pedido.observacion or "",
            "detalles": detalles,
        }
    )


@role_required("administrador", "supervisor", "preventista")
@require_http_methods(["POST"])
def editar_pedido(request, id: int):
    from django.utils.dateparse import parse_date
    
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    if pedido.estado != Pedido.ESTADO_PENDIENTE:
        messages.error(request, "Solo puedes editar pedidos pendientes")
        return redirect("listar_pedidos")

    observacion = (request.POST.get("observacion") or "").strip()
    fecha_entrega_estimada_raw = (request.POST.get("fecha_entrega_estimada") or "").strip()
    
    # Validar fecha de entrega estimada
    if not fecha_entrega_estimada_raw:
        messages.error(request, "Ingresa una fecha de entrega estimada")
        return redirect("listar_pedidos")
    
    fecha_entrega_estimada = parse_date(fecha_entrega_estimada_raw)
    if not fecha_entrega_estimada:
        messages.error(request, "Formato de fecha inválido")
        return redirect("listar_pedidos")
    
    hoy = date.today()
    if fecha_entrega_estimada < hoy:
        messages.error(request, "La fecha de entrega no puede ser menor a hoy")
        return redirect("listar_pedidos")
    
    producto_ids = request.POST.getlist("producto_id[]")
    cantidades = request.POST.getlist("cantidad[]")

    items = []
    for pid, cant in zip(producto_ids, cantidades):
        pid = (pid or "").strip()
        cant = (cant or "").strip()
        if not pid or not cant:
            continue
        try:
            cantidad_int = int(cant)
        except ValueError:
            continue
        if cantidad_int <= 0:
            continue
        items.append((pid, cantidad_int))

    if not items:
        messages.error(request, "Agrega al menos un producto con cantidad")
        return redirect("listar_pedidos")

    qty_por_pid = {}
    for pid, cantidad_int in items:
        qty_por_pid[pid] = int(qty_por_pid.get(pid, 0)) + int(cantidad_int)

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(id=pedido.id)

        detalles_previos = list(pedido.detalles.select_related("producto").all())
        qty_prev_por_pid = {}
        for det in detalles_previos:
            key = str(det.producto_id)
            qty_prev_por_pid[key] = int(qty_prev_por_pid.get(key, 0)) + int(det.cantidad or 0)

        productos = list(
            Producto.objects.select_for_update().filter(id__in=qty_por_pid.keys(), activo=True)
        )
        productos_por_id = {str(p.id): p for p in productos}

        for pid, cantidad_int in qty_por_pid.items():
            pid_key = str(pid)
            producto = productos_por_id.get(pid_key)
            if not producto:
                messages.error(request, "Producto inválido")
                return redirect("listar_pedidos")
            stock = int(getattr(producto, "stock_unidades", 0) or 0)
            # Si el pedido ya había descontado stock, lo disponible incluye lo reservado por este pedido.
            if pedido.stock_descontado:
                stock += int(qty_prev_por_pid.get(pid_key, 0))
            precio = producto.precio_unidad or Decimal("0.00")
            if cantidad_int > stock:
                messages.error(request, f'Stock insuficiente para "{producto.nombre}" (stock: {stock})')
                return redirect("listar_pedidos")
            if precio <= 0:
                messages.error(request, f'No puedes vender "{producto.nombre}" porque su precio es 0')
                return redirect("listar_pedidos")

        # Ajustar inventario y detalles recién cuando ya validó todo
        if pedido.stock_descontado:
            _reponer_stock_por_detalles(detalles_previos)

        pedido.observacion = observacion or None
        pedido.fecha_entrega_estimada = fecha_entrega_estimada
        pedido.detalles.all().delete()

        total = Decimal("0.00")
        detalles_creados = []
        for pid, cantidad_int in qty_por_pid.items():
            producto = productos_por_id.get(str(pid))
            precio = producto.precio_unidad or Decimal("0.00")
            subtotal = (precio * Decimal(cantidad_int)).quantize(Decimal("0.01"))
            det = DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=cantidad_int,
                precio_unitario=precio,
                subtotal=subtotal,
            )
            detalles_creados.append(det)
            total += subtotal

        pedido.total = total.quantize(Decimal("0.01"))
        _descontar_stock_por_detalles(detalles_creados)
        pedido.stock_descontado = True
        pedido.save(update_fields=["observacion", "fecha_entrega_estimada", "total", "stock_descontado"])

    messages.success(request, "Pedido actualizado")
    return redirect("listar_pedidos")


@role_required("repartidor")
def pedidos_mapa(request):
    return render(request, "pedidos/mapa.html")


@role_required("repartidor")
def pedidos_mapa_puntos(request):
    # Obtener preventistas asignados al repartidor
    perfil_repartidor = getattr(request.user, "perfil", None)
    preventistas_ids = PerfilUsuario.objects.filter(
        rol="preventista",
        repartidor=request.user,
        activo=True,
        usuario__is_active=True,
    ).values_list("usuario_id", flat=True)
    
    pedidos = (
        Pedido.objects.select_related("cliente")
        .filter(
            cliente__activo=True,
            cliente__latitud__isnull=False,
            cliente__longitud__isnull=False,
            preventista_id__in=preventistas_ids,
        )
        .order_by("-fecha")
    )

    # Filtrado opcional por fecha de entrega registrada (igualdad)
    fecha = (request.GET.get("fecha") or "").strip()
    if fecha:
        try:
            fecha_dt = date.fromisoformat(fecha)
            pedidos = pedidos.filter(fecha_entrega_estimada=fecha_dt)
        except Exception:
            # formato inválido -> ignorar
            pass

    puntos = []
    for p in pedidos:
        c = p.cliente
        puntos.append(
            {
                "pedido_id": p.id,
                "cliente": str(c),
                "lat": float(c.latitud),
                "lng": float(c.longitud),
                "direccion": c.direccion or "",
                "telefono": c.telefono or "",
                "ci_nit": c.ci_nit or "",
                "cliente_id": c.id,
                "foto_url": c.foto_tienda.url if getattr(c, "foto_tienda", None) else "",
                "descripcion": getattr(c, "descripcion", "") or "",
                "fecha": p.fecha.strftime("%d/%m/%Y %H:%M"),
                "fecha_entrega": p.fecha_entrega_estimada.strftime("%d/%m/%Y") if p.fecha_entrega_estimada else "-",
                "fecha_iso": p.fecha_entrega_estimada.isoformat() if p.fecha_entrega_estimada else "",
                "total": str(p.total),
                "estado_str": p.get_estado_display(),
                "estado": p.estado,
            }
        )

    return JsonResponse({"puntos": puntos})


@role_required("administrador")
@require_http_methods(["POST"])
def anular_pedido(request, id: int):
    pedido = get_object_or_404(Pedido, id=id)
    if pedido.estado == Pedido.ESTADO_VENDIDO:
        messages.error(request, "No puedes anular un pedido vendido")
        return redirect("listar_pedidos")

    if pedido.estado != Pedido.ESTADO_ANULADO:
        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(id=pedido.id)
            if pedido.stock_descontado:
                _reponer_stock_por_detalles(pedido.detalles.select_related("producto").all())
                pedido.stock_descontado = False
            pedido.estado = Pedido.ESTADO_ANULADO
            pedido.save(update_fields=["estado", "stock_descontado"])
        messages.success(request, "Pedido anulado")
    return redirect("listar_pedidos")


@role_required("preventista", "repartidor")
@require_http_methods(["POST"])
def marcar_vendido(request, id: int):
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    if pedido.estado in {Pedido.ESTADO_ANULADO, Pedido.ESTADO_NO_ENTREGADO}:
        messages.error(request, "No puedes marcar vendido este pedido")
        return redirect("listar_pedidos")

    if pedido.estado == Pedido.ESTADO_VENDIDO:
        messages.info(request, "Este pedido ya está marcado como vendido")
        return redirect("listar_pedidos")

    with transaction.atomic():
        # Lock del pedido para evitar doble marcado concurrente.
        pedido = Pedido.objects.select_for_update().get(id=pedido.id)
        if pedido.estado == Pedido.ESTADO_VENDIDO:
            messages.info(request, "Este pedido ya está marcado como vendido")
            return redirect("listar_pedidos")
        if pedido.estado == Pedido.ESTADO_ANULADO:
            messages.error(request, "No puedes marcar vendido un pedido anulado")
            return redirect("listar_pedidos")

        # Compatibilidad: pedidos antiguos que aún no descontaron stock
        if not pedido.stock_descontado:
            detalles = pedido.detalles.select_related("producto").all()
            _descontar_stock_por_detalles(detalles)
            pedido.stock_descontado = True

        pedido.estado = Pedido.ESTADO_VENDIDO
        pedido.fecha_vendido = timezone.now()
        pedido.save(update_fields=["estado", "fecha_vendido", "stock_descontado"])
    messages.success(request, "Pedido marcado como vendido")
    return redirect("listar_pedidos")


@role_required("repartidor")
@require_http_methods(["POST"])
def registrar_entrega(request, id: int):
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    if pedido.estado != Pedido.ESTADO_PENDIENTE:
        messages.error(request, "Solo puedes registrar entrega para pedidos pendientes")
        return redirect("listar_pedidos")

    resultado = (request.POST.get("resultado") or "").strip().lower()
    motivo_general = (request.POST.get("motivo_general") or "").strip()

    if resultado not in {"entregado_completo", "entregado_parcial", "no_entregado"}:
        messages.error(request, "Resultado de entrega inválido")
        return redirect("listar_pedidos")

    if resultado == "no_entregado":
        if not motivo_general:
            messages.error(request, "Debes indicar el motivo de no entrega")
            return redirect("listar_pedidos")

        with transaction.atomic():
            pedido = Pedido.objects.select_for_update().get(id=pedido.id)
            if not pedido.stock_descontado:
                _descontar_stock_por_detalles(pedido.detalles.select_related("producto").all())
                pedido.stock_descontado = True
            pedido.estado = Pedido.ESTADO_NO_ENTREGADO
            pedido.observacion = motivo_general
            pedido.save(update_fields=["estado", "observacion", "stock_descontado"])

            devolucion = DevolucionPedido.objects.create(
                pedido=pedido,
                repartidor=request.user,
                tipo=DevolucionPedido.TIPO_NO_ENTREGADO,
                motivo_general=motivo_general,
            )

            for det in pedido.detalles.select_related("producto").all():
                DevolucionItem.objects.create(
                    devolucion=devolucion,
                    detalle_pedido=det,
                    producto=det.producto,
                    cantidad_devuelta=det.cantidad,
                    motivo=motivo_general or "No entregado",
                )

            devolucion.actualizar_estado_reposicion(save=True)

        messages.success(request, "Pedido marcado como no entregado")
        return redirect("listar_pedidos")

    detalles = list(pedido.detalles.select_related("producto").all())
    cantidades_entregadas = {}
    errores = []

    for detalle in detalles:
        raw = (request.POST.get(f"cantidad_entregada_{detalle.id}") or "").strip()
        if raw == "":
            raw = str(detalle.cantidad if resultado == "entregado_completo" else 0)
        try:
            cant = int(raw)
        except ValueError:
            errores.append(f"Cantidad inválida para {detalle.producto.nombre}")
            continue

        if cant < 0:
            errores.append(f"Cantidad negativa para {detalle.producto.nombre}")
            continue
        if cant > detalle.cantidad:
            errores.append(
                f"Cantidad entregada para {detalle.producto.nombre} supera lo pedido ({detalle.cantidad})"
            )
            continue

        if resultado == "entregado_completo" and cant != detalle.cantidad:
            errores.append(
                f"En entrega completa, {detalle.producto.nombre} debe entregarse completo ({detalle.cantidad})"
            )
            continue
        cantidades_entregadas[str(detalle.id)] = cant

    if errores:
        messages.error(request, " | ".join(errores))
        return redirect("listar_pedidos")

    with transaction.atomic():
        pedido = Pedido.objects.select_for_update().get(id=pedido.id)

        devolucion = None
        total_devuelto = 0
        if resultado == "entregado_parcial":
            devolucion = DevolucionPedido.objects.create(
                pedido=pedido,
                repartidor=request.user,
                tipo=DevolucionPedido.TIPO_PARCIAL,
                motivo_general=motivo_general or None,
            )

        for det in detalles:
            entregada = cantidades_entregadas.get(str(det.id), 0)
            devuelta = max(det.cantidad - entregada, 0)

            if devuelta > 0 and devolucion is not None:
                DevolucionItem.objects.create(
                    devolucion=devolucion,
                    detalle_pedido=det,
                    producto=det.producto,
                    cantidad_devuelta=devuelta,
                    motivo=motivo_general or "Cantidad no entregada",
                )
                total_devuelto += devuelta

        if resultado == "entregado_parcial" and total_devuelto <= 0:
            devolucion.delete()
            messages.error(request, "Si eliges entrega parcial, debe existir al menos una devolución")
            return redirect("listar_pedidos")

        # El stock se descuenta al registrar el pedido; compatibilidad para pedidos antiguos.
        if not pedido.stock_descontado:
            _descontar_stock_por_detalles(pedido.detalles.select_related("producto").all())
            pedido.stock_descontado = True

        pedido.estado = Pedido.ESTADO_VENDIDO
        pedido.fecha_vendido = timezone.now()
        pedido.save(update_fields=["estado", "fecha_vendido", "stock_descontado"])

        if devolucion is not None:
            devolucion.actualizar_estado_reposicion(save=True)

    if resultado == "entregado_parcial":
        messages.success(request, "Entrega parcial registrada con devoluciones")
    else:
        messages.success(request, "Entrega completa registrada")
    return redirect("listar_pedidos")


def _devoluciones_qs_para_usuario(user):
    perfil = getattr(user, "perfil", None)
    qs = DevolucionPedido.objects.select_related("pedido", "pedido__cliente", "repartidor")
    if user.is_superuser:
        return qs
    if perfil and perfil.rol == "administrador":
        return qs
    if perfil and perfil.rol == "repartidor":
        return qs.filter(repartidor=user)
    return qs.none()


@role_required("administrador", "repartidor")
def listar_devoluciones(request):
    q = (request.GET.get("q") or "").strip()
    estado_reposicion = (request.GET.get("estado_reposicion") or "").strip().lower()
    tipo = (request.GET.get("tipo") or "").strip().lower()
    repartidor_raw = (request.GET.get("repartidor") or "").strip()
    fecha_desde = (request.GET.get("fecha_desde") or "").strip()
    fecha_hasta = (request.GET.get("fecha_hasta") or "").strip()

    devoluciones = _devoluciones_qs_para_usuario(request.user)
    if q:
        devoluciones = devoluciones.filter(
            Q(pedido__cliente__nombres__icontains=q)
            | Q(pedido__cliente__apellidos__icontains=q)
            | Q(pedido__id__icontains=q)
            | Q(repartidor__username__icontains=q)
        )

    estados_validos = {
        DevolucionPedido.ESTADO_PENDIENTE,
        DevolucionPedido.ESTADO_PARCIAL,
        DevolucionPedido.ESTADO_REPUESTO,
    }
    if estado_reposicion not in estados_validos:
        estado_reposicion = ""

    if estado_reposicion:
        devoluciones = devoluciones.filter(estado_reposicion=estado_reposicion)

    tipos_validos = {DevolucionPedido.TIPO_PARCIAL, DevolucionPedido.TIPO_NO_ENTREGADO}
    if tipo not in tipos_validos:
        tipo = ""
    if tipo:
        devoluciones = devoluciones.filter(tipo=tipo)

    repartidor_id = ""
    if repartidor_raw:
        try:
            repartidor_id_int = int(repartidor_raw)
        except ValueError:
            repartidor_id_int = None
        if repartidor_id_int is not None:
            devoluciones = devoluciones.filter(repartidor_id=repartidor_id_int)
            repartidor_id = str(repartidor_id_int)

    if fecha_desde:
        devoluciones = devoluciones.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        devoluciones = devoluciones.filter(fecha_creacion__date__lte=fecha_hasta)

    devoluciones = devoluciones.order_by("-fecha_creacion")

    base_qs = _devoluciones_qs_para_usuario(request.user)
    repartidor_ids = base_qs.values_list("repartidor_id", flat=True).distinct()
    repartidores = User.objects.filter(id__in=repartidor_ids).order_by("username")
    perfil = getattr(request.user, "perfil", None)
    # PAGINACIÓN (igual que usuarios/clientes)
    page = request.GET.get("page", 1)
    paginator = Paginator(devoluciones, 10)  # 10 devoluciones por página
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    is_admin = bool(request.user.is_superuser or (perfil and perfil.rol == "administrador"))

    return render(
        request,
        "devoluciones/devoluciones.html",
        {
            "devoluciones": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "q": q,
            "q": q,
            "estado_reposicion": estado_reposicion,
            "tipo": tipo,
            "repartidor": repartidor_id,
            "repartidores": repartidores,
            "fecha_desde": fecha_desde,
            "fecha_hasta": fecha_hasta,
            "is_admin": is_admin,
        },
    )


@role_required("administrador", "repartidor")
def obtener_devolucion(request, id: int):
    devolucion = get_object_or_404(_devoluciones_qs_para_usuario(request.user), id=id)

    items = []
    for it in devolucion.items.select_related("producto", "repuesto_por").all():
        items.append(
            {
                "id": it.id,
                "producto": it.producto.nombre,
                "cantidad_devuelta": it.cantidad_devuelta,
                "motivo": it.motivo or "",
                "repuesto": it.repuesto,
                "fecha_reposicion": it.fecha_reposicion.strftime("%d/%m/%Y %H:%M") if it.fecha_reposicion else "",
                "repuesto_por": (
                    (it.repuesto_por.get_full_name() or it.repuesto_por.username)
                    if it.repuesto_por
                    else ""
                ),
            }
        )

    return JsonResponse(
        {
            "id": devolucion.id,
            "pedido_id": devolucion.pedido_id,
            "cliente": f"{devolucion.pedido.cliente.nombres} {devolucion.pedido.cliente.apellidos or ''}".strip(),
            "repartidor": devolucion.repartidor.get_full_name() or devolucion.repartidor.username,
            "tipo": devolucion.get_tipo_display(),
            "motivo_general": devolucion.motivo_general or "",
            "estado_reposicion": devolucion.get_estado_reposicion_display(),
            "fecha": devolucion.fecha_creacion.strftime("%d/%m/%Y %H:%M"),
            "items": items,
            "is_admin": bool(request.user.is_superuser or (getattr(request.user, "perfil", None) and request.user.perfil.rol == "administrador")),
        }
    )


@role_required("administrador")
def resumen_reponer_devolucion(request, id: int):
    devolucion = get_object_or_404(DevolucionPedido.objects.select_related("pedido"), id=id)
    items = devolucion.items.select_related("producto").all()
    resumen = _resumen_reposicion_desde_items(items)

    return JsonResponse(
        {
            "ok": True,
            "devolucion_id": devolucion.id,
            "pedido_id": devolucion.pedido_id,
            "resumen": resumen,
        }
    )


@role_required("administrador")
def resumen_reponer_todo_devoluciones(request):
    q = (request.GET.get("q") or "").strip()
    estado_reposicion = (request.GET.get("estado_reposicion") or "").strip().lower()
    tipo = (request.GET.get("tipo") or "").strip().lower()
    repartidor_raw = (request.GET.get("repartidor") or "").strip()
    fecha_desde = (request.GET.get("fecha_desde") or "").strip()
    fecha_hasta = (request.GET.get("fecha_hasta") or "").strip()

    qs = _devoluciones_qs_para_usuario(request.user)
    if q:
        qs = qs.filter(
            Q(pedido__cliente__nombres__icontains=q)
            | Q(pedido__cliente__apellidos__icontains=q)
            | Q(pedido__id__icontains=q)
            | Q(repartidor__username__icontains=q)
        )
    if estado_reposicion in {
        DevolucionPedido.ESTADO_PENDIENTE,
        DevolucionPedido.ESTADO_PARCIAL,
        DevolucionPedido.ESTADO_REPUESTO,
    }:
        qs = qs.filter(estado_reposicion=estado_reposicion)
    if tipo in {DevolucionPedido.TIPO_PARCIAL, DevolucionPedido.TIPO_NO_ENTREGADO}:
        qs = qs.filter(tipo=tipo)
    if repartidor_raw:
        try:
            qs = qs.filter(repartidor_id=int(repartidor_raw))
        except ValueError:
            pass
    if fecha_desde:
        qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)

    items = DevolucionItem.objects.select_related("producto").filter(
        devolucion_id__in=qs.values_list("id", flat=True)
    )
    resumen = _resumen_reposicion_desde_items(items)

    return JsonResponse(
        {
            "ok": True,
            "resumen": resumen,
        }
    )


@role_required("administrador")
@require_http_methods(["POST"])
def reponer_devolucion_item(request, id: int):
    item = get_object_or_404(DevolucionItem.objects.select_related("producto", "devolucion"), id=id)
    with transaction.atomic():
        ok = _reponer_item_devolucion(item, request.user)

    if ok:
        messages.success(request, "Producto repuesto al stock correctamente")
    else:
        messages.info(request, "Este item ya fue repuesto")

    return redirect("listar_devoluciones")


@role_required("administrador")
@require_http_methods(["POST"])
def reponer_devolucion(request, id: int):
    devolucion = get_object_or_404(
        DevolucionPedido.objects.select_related("pedido", "repartidor"),
        id=id,
    )

    repuestos = 0
    with transaction.atomic():
        for item in devolucion.items.select_related("producto").all():
            if _reponer_item_devolucion(item, request.user):
                repuestos += 1

    if repuestos:
        messages.success(request, f"Se repusieron {repuestos} item(s) de la devolución")
    else:
        messages.info(request, "Esta devolución no tiene items pendientes de reposición")

    return redirect("listar_devoluciones")


@role_required("administrador")
@require_http_methods(["POST"])
def reponer_todo_devoluciones(request):
    q = (request.POST.get("q") or "").strip()
    estado_reposicion = (request.POST.get("estado_reposicion") or "").strip().lower()
    tipo = (request.POST.get("tipo") or "").strip().lower()
    repartidor_raw = (request.POST.get("repartidor") or "").strip()
    fecha_desde = (request.POST.get("fecha_desde") or "").strip()
    fecha_hasta = (request.POST.get("fecha_hasta") or "").strip()

    qs = _devoluciones_qs_para_usuario(request.user)
    if q:
        qs = qs.filter(
            Q(pedido__cliente__nombres__icontains=q)
            | Q(pedido__cliente__apellidos__icontains=q)
            | Q(pedido__id__icontains=q)
            | Q(repartidor__username__icontains=q)
        )
    if estado_reposicion in {
        DevolucionPedido.ESTADO_PENDIENTE,
        DevolucionPedido.ESTADO_PARCIAL,
        DevolucionPedido.ESTADO_REPUESTO,
    }:
        qs = qs.filter(estado_reposicion=estado_reposicion)
    if tipo in {DevolucionPedido.TIPO_PARCIAL, DevolucionPedido.TIPO_NO_ENTREGADO}:
        qs = qs.filter(tipo=tipo)
    if repartidor_raw:
        try:
            qs = qs.filter(repartidor_id=int(repartidor_raw))
        except ValueError:
            pass
    if fecha_desde:
        qs = qs.filter(fecha_creacion__date__gte=fecha_desde)
    if fecha_hasta:
        qs = qs.filter(fecha_creacion__date__lte=fecha_hasta)

    repuestos = 0
    with transaction.atomic():
        items = DevolucionItem.objects.select_related("devolucion", "producto").filter(
            devolucion_id__in=qs.values_list("id", flat=True),
            repuesto=False,
        )
        for item in items:
            if _reponer_item_devolucion(item, request.user):
                repuestos += 1

    if repuestos:
        messages.success(request, f"Reposición masiva completada. Items repuestos: {repuestos}")
    else:
        messages.info(request, "No hay items pendientes para reponer con los filtros actuales")

    return redirect("listar_devoluciones")
