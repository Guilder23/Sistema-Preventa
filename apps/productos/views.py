from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.usuarios.decorators import role_required

from .models import Producto


@login_required
def listar_productos(request):
    q = (request.GET.get("q") or "").strip()
    productos = Producto.objects.all().order_by("nombre")
    if q:
        productos = productos.filter(Q(nombre__icontains=q) | Q(codigo__icontains=q))
    return render(request, "productos/productos.html", {"productos": productos, "q": q})


@role_required("administrador")
@require_http_methods(["POST"])
def crear_producto(request):
    codigo = (request.POST.get("codigo") or "").strip()
    nombre = (request.POST.get("nombre") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    precio_unidad = request.POST.get("precio_unidad") or "0"
    precio_mayor = request.POST.get("precio_mayor") or "0"
    precio_caja = request.POST.get("precio_caja") or "0"
    foto = request.FILES.get("foto")

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
        precio_mayor=precio_mayor or 0,
        precio_caja=precio_caja or 0,
        foto=foto,
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
            "precio_mayor": str(producto.precio_mayor),
            "precio_caja": str(producto.precio_caja),
            "activo": producto.activo,
            "foto_url": producto.foto.url if producto.foto else None,
        }
    )


@role_required("administrador")
@require_http_methods(["POST"])
def editar_producto(request, id: int):
    producto = get_object_or_404(Producto, id=id)
    nombre = (request.POST.get("nombre") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    precio_unidad = request.POST.get("precio_unidad") or "0"
    precio_mayor = request.POST.get("precio_mayor") or "0"
    precio_caja = request.POST.get("precio_caja") or "0"
    foto = request.FILES.get("foto")
    activo = request.POST.get("activo") == "on"

    if not nombre:
        messages.error(request, "El nombre es obligatorio")
        return redirect("listar_productos")

    producto.nombre = nombre
    producto.descripcion = descripcion or None
    producto.precio_unidad = precio_unidad or 0
    producto.precio_mayor = precio_mayor or 0
    producto.precio_caja = precio_caja or 0
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
