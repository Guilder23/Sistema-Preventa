from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_http_methods

from apps.clientes.models import Cliente
from apps.productos.models import Producto
from apps.usuarios.decorators import role_required

from .models import DetallePedido, Pedido


def _clientes_para_usuario(user):
    perfil = getattr(user, "perfil", None)
    qs = Cliente.objects.filter(activo=True)
    if user.is_superuser:
        return qs
    if perfil and perfil.rol == "administrador":
        return qs
    return qs.filter(creado_por=user)


def _pedidos_qs_para_usuario(user):
    perfil = getattr(user, "perfil", None)
    qs = Pedido.objects.select_related("cliente", "preventista")
    if user.is_superuser:
        return qs
    if perfil and perfil.rol == "administrador":
        return qs
    return qs.filter(preventista=user)


@login_required
def listar_pedidos(request):
    q = (request.GET.get("q") or "").strip()
    pedidos = _pedidos_qs_para_usuario(request.user)

    if q:
        pedidos = pedidos.filter(
            Q(cliente__nombres__icontains=q)
            | Q(cliente__apellidos__icontains=q)
            | Q(cliente__ci_nit__icontains=q)
        )

    clientes = _clientes_para_usuario(request.user).order_by("nombres", "apellidos")
    productos = Producto.objects.filter(activo=True).order_by("nombre")

    return render(
        request,
        "pedidos/pedidos.html",
        {
            "pedidos": pedidos,
            "q": q,
            "clientes": clientes,
            "productos": productos,
        },
    )


@login_required
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

    with transaction.atomic():
        pedido = Pedido.objects.create(
            cliente=cliente,
            preventista=request.user,
            observacion=observacion or None,
        )

        total = Decimal("0.00")
        for pid, cantidad_int in items:
            producto = get_object_or_404(Producto, id=pid, activo=True)
            precio = producto.precio_unidad or Decimal("0.00")
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


@login_required
def obtener_pedido(request, id: int):
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    detalles = (
        pedido.detalles.select_related("producto")
        .all()
        .values(
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


@role_required("preventista")
@require_http_methods(["POST"])
def marcar_vendido(request, id: int):
    pedido = get_object_or_404(_pedidos_qs_para_usuario(request.user), id=id)

    if pedido.estado == Pedido.ESTADO_ANULADO:
        messages.error(request, "No puedes marcar vendido un pedido anulado")
        return redirect("listar_pedidos")

    if pedido.estado == Pedido.ESTADO_VENDIDO:
        messages.info(request, "Este pedido ya está marcado como vendido")
        return redirect("listar_pedidos")

    pedido.estado = Pedido.ESTADO_VENDIDO
    pedido.fecha_vendido = timezone.now()
    pedido.save(update_fields=["estado", "fecha_vendido"])
    messages.success(request, "Pedido marcado como vendido")
    return redirect("listar_pedidos")
