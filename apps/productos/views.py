from __future__ import annotations

from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import Q
from django.db.models import Sum
from django.db.models import Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.usuarios.decorators import role_required

from .models import MovimientoInventario, Producto


@login_required
def listar_productos(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    stock = (request.GET.get("stock") or "").strip().lower()
    productos = Producto.objects.all().order_by("nombre")
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))

    if estado not in {"activo", "inactivo"}:
        estado = ""
    if estado == "activo":
        productos = productos.filter(activo=True)
    elif estado == "inactivo":
        productos = productos.filter(activo=False)

    if stock not in {"verde", "amarillo", "rojo"}:
        stock = ""
    if stock == "rojo":
        productos = productos.filter(stock_unidades__lte=F("stock_umbral_rojo"))
    elif stock == "amarillo":
        productos = productos.filter(
            stock_unidades__gt=F("stock_umbral_rojo"),
            stock_unidades__lte=F("stock_umbral_amarillo"),
        )
    elif stock == "verde":
        productos = productos.filter(stock_unidades__gt=F("stock_umbral_amarillo"))

    productos = productos.annotate(
        stock_agregado=Coalesce(
            Sum(
                "movimientos_inventario__cantidad",
                filter=Q(
                    movimientos_inventario__tipo=MovimientoInventario.TIPO_ENTRADA
                ),
            ),
            Value(0),
            output_field=IntegerField(),
        )
    )

    return render(
        request,
        "productos/productos.html",
        {
            "productos": productos,
            "q": q,
            "estado": estado,
            "stock": stock,
        },
    )


@role_required("administrador")
@require_http_methods(["POST"])
def crear_producto(request):
    codigo = (request.POST.get("codigo") or "").strip()
    nombre = (request.POST.get("nombre") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    precio_unidad = request.POST.get("precio_unidad") or "0"
    precio_caja = request.POST.get("precio_caja") or "0"
    precio_compra_unidad = request.POST.get("precio_compra_unidad") or "0"
    precio_compra_caja = request.POST.get("precio_compra_caja") or "0"
    foto = request.FILES.get("foto")
    stock_umbral_amarillo = (request.POST.get("stock_umbral_amarillo") or "10").strip()
    stock_umbral_rojo = (request.POST.get("stock_umbral_rojo") or "3").strip()

    if not codigo or not nombre:
        messages.error(request, "Código y nombre son obligatorios")
        return redirect("listar_productos")
    if Producto.objects.filter(codigo=codigo).exists():
        messages.error(request, f'El código "{codigo}" ya existe')
        return redirect("listar_productos")

    Producto.objects.create(
        codigo=codigo,
        nombre=nombre,
        descripcion=descripcion or None,
        precio_unidad=precio_unidad or 0,
        precio_caja=precio_caja or 0,
        precio_compra_unidad=precio_compra_unidad or 0,
        precio_compra_caja=precio_compra_caja or 0,
        foto=foto,
        stock_unidades=0,
        stock_umbral_amarillo=stock_umbral_amarillo or 10,
        stock_umbral_rojo=stock_umbral_rojo or 3,
        creado_por=request.user,
    )
    messages.success(request, "Producto creado correctamente")
    return redirect("listar_productos")


@login_required
def obtener_producto(request, id: int):
    producto = get_object_or_404(Producto, id=id)
    return JsonResponse(
        {
            "id": producto.id,
            "codigo": producto.codigo,
            "nombre": producto.nombre,
            "descripcion": producto.descripcion or "",
            "precio_unidad": str(producto.precio_unidad),
            "precio_caja": str(producto.precio_caja),
            "precio_compra_unidad": str(producto.precio_compra_unidad),
            "precio_compra_caja": str(producto.precio_compra_caja),
            "activo": producto.activo,
            "foto_url": producto.foto.url if producto.foto else None,
            "stock_unidades": producto.stock_unidades,
            "stock_umbral_amarillo": producto.stock_umbral_amarillo,
            "stock_umbral_rojo": producto.stock_umbral_rojo,
        }
    )


@role_required("administrador")
def obtener_inventario_producto(request, id: int):
    producto = get_object_or_404(Producto, id=id)
    movimientos = list(
        producto.movimientos_inventario.select_related("usuario").order_by("-fecha", "-id")[:12]
    )

    return JsonResponse(
        {
            "id": producto.id,
            "codigo": producto.codigo,
            "nombre": producto.nombre,
            "stock_actual": producto.stock_unidades,
            "precio_compra_unidad": str(producto.precio_compra_unidad),
            "valor_inventario_compra": str((producto.stock_unidades or 0) * (producto.precio_compra_unidad or Decimal("0.00"))),
            "movimientos": [
                {
                    "id": mov.id,
                    "tipo": mov.tipo,
                    "tipo_display": mov.get_tipo_display(),
                    "cantidad": mov.cantidad,
                    "stock_anterior": mov.stock_anterior,
                    "stock_nuevo": mov.stock_nuevo,
                    "precio_compra_unitario": str(mov.precio_compra_unitario),
                    "valor_compra_total": str(mov.valor_compra_total),
                    "motivo": mov.motivo or "",
                    "usuario": (mov.usuario.get_full_name() or mov.usuario.username) if mov.usuario else "-",
                    "fecha": mov.fecha.strftime("%d/%m/%Y %H:%M") if mov.fecha else "-",
                }
                for mov in movimientos
            ],
        }
    )


@role_required("administrador")
@require_http_methods(["POST"])
def ajustar_inventario_producto(request, id: int):
    producto = get_object_or_404(Producto, id=id)
    tipo = (request.POST.get("tipo") or "").strip().lower()
    cantidad_raw = (request.POST.get("cantidad") or "0").strip()
    motivo = (request.POST.get("motivo") or "").strip()

    try:
        cantidad = int(cantidad_raw)
    except ValueError:
        cantidad = 0

    if tipo not in {MovimientoInventario.TIPO_ENTRADA, MovimientoInventario.TIPO_SALIDA}:
        messages.error(request, "Selecciona un tipo de ajuste válido")
        return redirect("listar_productos")

    if cantidad <= 0:
        messages.error(request, "La cantidad debe ser mayor que cero")
        return redirect("listar_productos")

    with transaction.atomic():
        producto = Producto.objects.select_for_update().get(id=producto.id)
        stock_anterior = int(producto.stock_unidades or 0)

        if tipo == MovimientoInventario.TIPO_ENTRADA:
            stock_nuevo = stock_anterior + cantidad
            valor_compra_total = Decimal(cantidad) * (producto.precio_compra_unidad or Decimal("0.00"))
        else:
            if cantidad > stock_anterior:
                messages.error(request, "No puedes retirar más unidades de las que hay en stock")
                return redirect("listar_productos")
            stock_nuevo = stock_anterior - cantidad
            valor_compra_total = Decimal(cantidad) * (producto.precio_compra_unidad or Decimal("0.00"))

        producto.stock_unidades = stock_nuevo
        producto.save(update_fields=["stock_unidades", "fecha_actualizacion"])

        MovimientoInventario.objects.create(
            producto=producto,
            tipo=tipo,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=stock_nuevo,
            precio_compra_unitario=producto.precio_compra_unidad or Decimal("0.00"),
            valor_compra_total=valor_compra_total,
            motivo=motivo or None,
            usuario=request.user,
        )

    if tipo == MovimientoInventario.TIPO_ENTRADA:
        messages.success(request, f"Se agregaron {cantidad} unidades al inventario")
    else:
        messages.success(request, f"Se retiraron {cantidad} unidades del inventario")
    return redirect("listar_productos")


@role_required("administrador")
@require_http_methods(["POST"])
def editar_producto(request, id: int):
    producto = get_object_or_404(Producto, id=id)
    nombre = (request.POST.get("nombre") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    precio_unidad = request.POST.get("precio_unidad") or "0"
    precio_caja = request.POST.get("precio_caja") or "0"
    precio_compra_unidad = request.POST.get("precio_compra_unidad") or "0"
    precio_compra_caja = request.POST.get("precio_compra_caja") or "0"
    foto = request.FILES.get("foto")
    activo = request.POST.get("activo") == "on"
    stock_umbral_amarillo = (request.POST.get("stock_umbral_amarillo") or "10").strip()
    stock_umbral_rojo = (request.POST.get("stock_umbral_rojo") or "3").strip()

    if not nombre:
        messages.error(request, "El nombre es obligatorio")
        return redirect("listar_productos")

    producto.nombre = nombre
    producto.descripcion = descripcion or None
    producto.precio_unidad = precio_unidad or 0
    producto.precio_caja = precio_caja or 0
    producto.precio_compra_unidad = precio_compra_unidad or 0
    producto.precio_compra_caja = precio_compra_caja or 0
    producto.stock_umbral_amarillo = stock_umbral_amarillo or 10
    producto.stock_umbral_rojo = stock_umbral_rojo or 3
    producto.activo = activo
    if foto:
        producto.foto = foto
    producto.save()

    messages.success(request, "Producto actualizado correctamente")
    return redirect("listar_productos")


@role_required("administrador")
@require_http_methods(["POST"])
def bloquear_producto(request, id: int):
    producto = get_object_or_404(Producto, id=id)
    producto.activo = not producto.activo
    producto.save(update_fields=["activo"])
    messages.success(request, "Producto activado" if producto.activo else "Producto bloqueado")
    return redirect("listar_productos")
