from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.usuarios.decorators import role_required

from .models import Cliente


def _clientes_qs_para_usuario(user):
    perfil = getattr(user, "perfil", None)
    qs = Cliente.objects.all()
    if user.is_superuser:
        return qs
    if perfil and perfil.rol == "administrador":
        return qs
    # preventista: solo los creados por él
    return qs.filter(creado_por=user)


@login_required
def listar_clientes(request):
    q = (request.GET.get("q") or "").strip()
    clientes = _clientes_qs_para_usuario(request.user).order_by("-fecha_creacion")
    if q:
        clientes = clientes.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(ci_nit__icontains=q)
            | Q(telefono__icontains=q)
        )
    return render(request, "clientes/clientes.html", {"clientes": clientes, "q": q})


@login_required
@require_http_methods(["POST"])
def crear_cliente(request):
    nombres = (request.POST.get("nombres") or "").strip()
    apellidos = (request.POST.get("apellidos") or "").strip()
    ci_nit = (request.POST.get("ci_nit") or "").strip()
    telefono = (request.POST.get("telefono") or "").strip()
    direccion = (request.POST.get("direccion") or "").strip()
    latitud = (request.POST.get("latitud") or "").strip()
    longitud = (request.POST.get("longitud") or "").strip()

    if not nombres:
        messages.error(request, "El nombre es obligatorio")
        return redirect("listar_clientes")

    Cliente.objects.create(
        nombres=nombres,
        apellidos=apellidos or None,
        ci_nit=ci_nit or None,
        telefono=telefono or None,
        direccion=direccion or None,
        latitud=latitud or None,
        longitud=longitud or None,
        creado_por=request.user,
    )
    messages.success(request, "Cliente registrado")
    return redirect("listar_clientes")


@login_required
def obtener_cliente(request, id: int):
    cliente = get_object_or_404(_clientes_qs_para_usuario(request.user), id=id)
    return JsonResponse(
        {
            "id": cliente.id,
            "nombres": cliente.nombres,
            "apellidos": cliente.apellidos or "",
            "ci_nit": cliente.ci_nit or "",
            "telefono": cliente.telefono or "",
            "direccion": cliente.direccion or "",
            "latitud": str(cliente.latitud) if cliente.latitud is not None else "",
            "longitud": str(cliente.longitud) if cliente.longitud is not None else "",
            "activo": cliente.activo,
        }
    )


@login_required
@require_http_methods(["POST"])
def editar_cliente(request, id: int):
    cliente = get_object_or_404(_clientes_qs_para_usuario(request.user), id=id)
    nombres = (request.POST.get("nombres") or "").strip()
    apellidos = (request.POST.get("apellidos") or "").strip()
    ci_nit = (request.POST.get("ci_nit") or "").strip()
    telefono = (request.POST.get("telefono") or "").strip()
    direccion = (request.POST.get("direccion") or "").strip()
    latitud = (request.POST.get("latitud") or "").strip()
    longitud = (request.POST.get("longitud") or "").strip()
    activo = request.POST.get("activo") == "on"

    if not nombres:
        messages.error(request, "El nombre es obligatorio")
        return redirect("listar_clientes")

    cliente.nombres = nombres
    cliente.apellidos = apellidos or None
    cliente.ci_nit = ci_nit or None
    cliente.telefono = telefono or None
    cliente.direccion = direccion or None
    cliente.latitud = latitud or None
    cliente.longitud = longitud or None
    cliente.activo = activo
    cliente.save()

    messages.success(request, "Cliente actualizado")
    return redirect("listar_clientes")


@role_required("administrador")
@require_http_methods(["POST"])
def bloquear_cliente(request, id: int):
    cliente = get_object_or_404(Cliente, id=id)
    cliente.activo = not cliente.activo
    cliente.save(update_fields=["activo"])
    messages.success(request, "Cliente activado" if cliente.activo else "Cliente bloqueado")
    return redirect("listar_clientes")
