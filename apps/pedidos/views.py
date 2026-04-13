from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.db.models import F
from django.db.models.functions import Greatest
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.usuarios.decorators import role_required
from apps.usuarios.models import PerfilUsuario

from .models import DetallePedido, Pedido


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


def _pedidos_qs_para_usuario(user):
    perfil = getattr(user, "perfil", None)
    qs = Pedido.objects.select_related("cliente", "preventista")
    if user.is_superuser:
        return qs
    if perfil and perfil.rol == "administrador":
        return qs
    if perfil and perfil.rol == "repartidor":
        return qs.filter(estado=Pedido.ESTADO_PENDIENTE)
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

    if estado not in {Pedido.ESTADO_PENDIENTE, Pedido.ESTADO_VENDIDO, Pedido.ESTADO_ANULADO}:
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

    perfil = getattr(request.user, "perfil", None)
    if perfil and perfil.rol == "repartidor":
        clientes = Cliente.objects.none()
        productos = Producto.objects.none()
        clientes_data = []
        productos_data = []
    else:
        clientes = _clientes_para_usuario(request.user).order_by("nombres", "apellidos")
        productos = Producto.objects.filter(activo=True).order_by("nombre")

        clientes_data = []
        for c in clientes:
            label = f"{c.nombres}{(' ' + c.apellidos) if c.apellidos else ''}{(' - ' + c.ci_nit) if c.ci_nit else ''}"
            clientes_data.append({"id": c.id, "label": label})

        productos_data = []
        for p in productos:
            label = f"{p.codigo} - {p.nombre}" if p.codigo else p.nombre
            productos_data.append(
                {
                    "id": p.id,
                    "label": label,
                    "precio": str(p.precio_unidad or Decimal('0.00')),
                    "stock": int(getattr(p, 'stock_unidades', 0) or 0),
                }
            )

    return render(
        request,
        "pedidos/pedidos.html",
        {
            "pedidos": pedidos,
            "q": q,
            "estado": estado,
            "rol_usuario": rol_usuario,
            "fecha_desde": fecha_desde_raw,
            "fecha_hasta": fecha_hasta_raw,
            "clientes": clientes,
            "productos": productos,
            "clientes_data": clientes_data,
            "productos_data": productos_data,
        },
    )


@role_required("administrador", "supervisor", "preventista")
@require_http_methods(["POST"])
def crear_pedido(request):
    cliente_id = (request.POST.get("cliente_id") or "").strip()
    observacion = (request.POST.get("observacion") or "").strip()

    producto_ids = request.POST.getlist("producto_id[]")
    cantidades = request.POST.getlist("cantidad[]")

    if not cliente_id:
        messages.error(request, "Selecciona un cliente")
        return redirect("listar_pedidos")

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
        return redirect("listar_pedidos")

    items_validos = []
    for pid, cantidad_int in items:
        producto = get_object_or_404(Producto, id=pid, activo=True)
        stock = int(getattr(producto, "stock_unidades", 0) or 0)
        precio = producto.precio_unidad or Decimal("0.00")

        if cantidad_int > stock:
            messages.error(request, f'Stock insuficiente para "{producto.nombre}" (stock: {stock})')
            return redirect("listar_pedidos")

        if precio <= 0:
            messages.error(request, f'No puedes vender "{producto.nombre}" porque su precio es 0')
            return redirect("listar_pedidos")

        items_validos.append((producto, cantidad_int, precio))

    with transaction.atomic():
        preventista_asignado = cliente.creado_por or request.user
        pedido = Pedido.objects.create(
            cliente=cliente,
            preventista=preventista_asignado,
            observacion=observacion or None,
        )

        total = Decimal("0.00")
        for producto, cantidad_int, precio in items_validos:
            subtotal = (precio * Decimal(cantidad_int)).quantize(Decimal("0.01"))
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=cantidad_int,
                precio_unitario=precio,
                subtotal=subtotal,
            )
            total += subtotal

        pedido.total = total.quantize(Decimal("0.01"))
        pedido.save(update_fields=["total"])

    messages.success(request, "Pedido creado")
    return redirect("listar_pedidos")


@role_required("administrador", "supervisor", "preventista", "repartidor")
def obtener_pedido(request, id: int):
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    detalles = (
        pedido.detalles.select_related("producto")
        .all()
        .values(
            "producto_id",
            "producto__nombre",
            "cantidad",
            "precio_unitario",
            "subtotal",
        )
    )

    return JsonResponse(
        {
            "id": pedido.id,
            "cliente": f"{pedido.cliente.nombres} {pedido.cliente.apellidos or ''}".strip(),
            "preventista": pedido.preventista.get_full_name() or pedido.preventista.username,
            "fecha": pedido.fecha.strftime("%d/%m/%Y %H:%M"),
            "estado": pedido.estado,
            "total": str(pedido.total),
            "observacion": pedido.observacion or "",
            "detalles": list(detalles),
        }
    )


@role_required("administrador", "supervisor", "preventista")
@require_http_methods(["POST"])
def editar_pedido(request, id: int):
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    if pedido.estado != Pedido.ESTADO_PENDIENTE:
        messages.error(request, "Solo puedes editar pedidos pendientes")
        return redirect("listar_pedidos")

    observacion = (request.POST.get("observacion") or "").strip()
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

    items_validos = []
    for pid, cantidad_int in items:
        producto = get_object_or_404(Producto, id=pid, activo=True)
        stock = int(getattr(producto, "stock_unidades", 0) or 0)
        precio = producto.precio_unidad or Decimal("0.00")

        if cantidad_int > stock:
            messages.error(request, f'Stock insuficiente para "{producto.nombre}" (stock: {stock})')
            return redirect("listar_pedidos")

        if precio <= 0:
            messages.error(request, f'No puedes vender "{producto.nombre}" porque su precio es 0')
            return redirect("listar_pedidos")

        items_validos.append((producto, cantidad_int, precio))

    with transaction.atomic():
        pedido.observacion = observacion or None
        pedido.detalles.all().delete()

        total = Decimal("0.00")
        for producto, cantidad_int, precio in items_validos:
            subtotal = (precio * Decimal(cantidad_int)).quantize(Decimal("0.01"))
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=cantidad_int,
                precio_unitario=precio,
                subtotal=subtotal,
            )
            total += subtotal

        pedido.total = total.quantize(Decimal("0.01"))
        pedido.save(update_fields=["observacion", "total"])

    messages.success(request, "Pedido actualizado")
    return redirect("listar_pedidos")


@role_required("repartidor")
def pedidos_mapa(request):
    return render(request, "pedidos/mapa.html")


@role_required("repartidor")
def pedidos_mapa_puntos(request):
    pedidos = (
        Pedido.objects.select_related("cliente")
        .filter(
            cliente__activo=True,
            cliente__latitud__isnull=False,
            cliente__longitud__isnull=False,
        )
        .order_by("-fecha")
    )

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
                "fecha": p.fecha.strftime("%d/%m/%Y %H:%M"),
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
        pedido.estado = Pedido.ESTADO_ANULADO
        pedido.save(update_fields=["estado"])
        messages.success(request, "Pedido anulado")
    return redirect("listar_pedidos")


@role_required("preventista", "repartidor")
@require_http_methods(["POST"])
def marcar_vendido(request, id: int):
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    if pedido.estado == Pedido.ESTADO_ANULADO:
        messages.error(request, "No puedes marcar vendido un pedido anulado")
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

        # Descontar stock por cada detalle (no deja stock en negativo)
        detalles = pedido.detalles.select_related("producto").all()
        for det in detalles:
            Producto.objects.filter(id=det.producto_id).update(
                stock_unidades=Greatest(F("stock_unidades") - det.cantidad, 0)
            )

        pedido.estado = Pedido.ESTADO_VENDIDO
        pedido.fecha_vendido = timezone.now()
        pedido.save(update_fields=["estado", "fecha_vendido"])
    messages.success(request, "Pedido marcado como vendido")
    return redirect("listar_pedidos")
