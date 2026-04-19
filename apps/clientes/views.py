from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods

from apps.usuarios.decorators import role_required
from apps.usuarios.models import PerfilUsuario

from .models import Cliente


def _clientes_qs_para_usuario(user):
    perfil = getattr(user, "perfil", None)
    qs = Cliente.objects.all()
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
    # preventista: solo los creados por él
    return qs.filter(creado_por=user)


@role_required("administrador", "supervisor", "preventista")
def listar_clientes(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    vendedor_raw = (request.GET.get("vendedor") or "").strip()

    clientes_base = _clientes_qs_para_usuario(request.user)

    # Vendedores disponibles dentro del alcance del usuario
    vendedor_ids = (
        clientes_base.exclude(creado_por__isnull=True)
        .values_list("creado_por_id", flat=True)
        .distinct()
    )
    vendedores = User.objects.filter(id__in=vendedor_ids).order_by("username")

    # Normalizar estado
    if estado not in {"activo", "inactivo"}:
        estado = ""

    # Validar vendedor
    vendedor_id = None
    if vendedor_raw:
        try:
            vendedor_id = int(vendedor_raw)
        except ValueError:
            vendedor_id = None
        else:
            if vendedor_id not in set(vendedor_ids):
                vendedor_id = None

    clientes = clientes_base.order_by("-fecha_creacion")
    if q:
        clientes = clientes.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(ci_nit__icontains=q)
            | Q(telefono__icontains=q)
        )

    if estado == "activo":
        clientes = clientes.filter(activo=True)
    elif estado == "inactivo":
        clientes = clientes.filter(activo=False)

    if vendedor_id is not None:
        clientes = clientes.filter(creado_por_id=vendedor_id)

    # PAGINACIÓN
    from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
    page = request.GET.get("page", 1)
    paginator = Paginator(clientes, 10)  # 10 clientes por página
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(
        request,
        "clientes/clientes.html",
        {
            "clientes": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "q": q,
            "estado": estado,
            "vendedor": str(vendedor_id) if vendedor_id is not None else "",
            "vendedores": vendedores,
        },
    )


@role_required("administrador", "supervisor", "preventista")
@role_required("administrador", "supervisor", "preventista")
def clientes_mapa(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    vendedor_raw = (request.GET.get("vendedor") or "").strip()

    clientes_base = _clientes_qs_para_usuario(request.user)
    vendedor_ids = (
        clientes_base.exclude(creado_por__isnull=True)
        .values_list("creado_por_id", flat=True)
        .distinct()
    )
    vendedores = User.objects.filter(id__in=vendedor_ids).order_by("username")

    # Normalizar estado
    if estado not in {"activo", "inactivo"}:
        estado = ""

    # Validar vendedor
    vendedor_id = None
    if vendedor_raw:
        try:
            vendedor_id = int(vendedor_raw)
        except ValueError:
            vendedor_id = None
        else:
            if vendedor_id not in set(vendedor_ids):
                vendedor_id = None

    return render(
        request,
        "clientes/mapa.html",
        {
            "q": q,
            "estado": estado,
            "vendedor": str(vendedor_id) if vendedor_id is not None else "",
            "vendedores": vendedores,
        },
    )


@role_required("administrador", "supervisor", "preventista")
def clientes_mapa_puntos(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    vendedor_raw = (request.GET.get("vendedor") or "").strip()

    clientes_base = _clientes_qs_para_usuario(request.user)
    vendedor_ids = (
        clientes_base.exclude(creado_por__isnull=True)
        .values_list("creado_por_id", flat=True)
        .distinct()
    )

    # Normalizar estado
    if estado not in {"activo", "inactivo"}:
        estado = ""

    # Validar vendedor
    vendedor_id = None
    if vendedor_raw:
        try:
            vendedor_id = int(vendedor_raw)
        except ValueError:
            vendedor_id = None
        else:
            if vendedor_id not in set(vendedor_ids):
                vendedor_id = None

    qs = clientes_base.filter(latitud__isnull=False, longitud__isnull=False)
    if q:
        qs = qs.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(ci_nit__icontains=q)
            | Q(telefono__icontains=q)
        )
    if estado == "activo":
        qs = qs.filter(activo=True)
    elif estado == "inactivo":
        qs = qs.filter(activo=False)
    if vendedor_id is not None:
        qs = qs.filter(creado_por_id=vendedor_id)
    qs = qs.order_by("nombres", "apellidos")

    puntos = []
    for c in qs:
        puntos.append(
            {
                "id": c.id,
                "nombre": str(c),
                "lat": float(c.latitud),
                "lng": float(c.longitud),
                "direccion": c.direccion or "",
                "telefono": c.telefono or "",
                "ci_nit": c.ci_nit or "",
            }
        )

    return JsonResponse({"puntos": puntos})


@role_required("administrador", "supervisor", "preventista")
@require_http_methods(["POST"])
def crear_cliente(request):
    nombres = (request.POST.get("nombres") or "").strip()
    apellidos = (request.POST.get("apellidos") or "").strip()
    ci_nit = (request.POST.get("ci_nit") or "").strip()
    telefono = (request.POST.get("telefono") or "").strip()
    direccion = (request.POST.get("direccion") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    latitud = (request.POST.get("latitud") or "").strip()
    longitud = (request.POST.get("longitud") or "").strip()
    foto_tienda = request.FILES.get("foto_tienda")

    if not nombres:
        messages.error(request, "El nombre es obligatorio")
        return redirect("listar_clientes")

    Cliente.objects.create(
        nombres=nombres,
        apellidos=apellidos or None,
        ci_nit=ci_nit or None,
        telefono=telefono or None,
        direccion=direccion or None,
        descripcion=descripcion or None,
        latitud=latitud or None,
        longitud=longitud or None,
        foto_tienda=foto_tienda,
        creado_por=request.user,
    )
    messages.success(request, "Cliente registrado")
    return redirect("listar_clientes")


@role_required("administrador", "supervisor", "preventista")
def obtener_cliente(request, id: int):
    cliente = get_object_or_404(_clientes_qs_para_usuario(request.user), id=id)
    
    # Obtener rol del creador
    rol_creador = ""
    if cliente.creado_por:
        perfil = getattr(cliente.creado_por, "perfil", None)
        if perfil:
            rol_creador = perfil.get_rol_display()
        elif cliente.creado_por.is_superuser:
            rol_creador = "Administrador"

    return JsonResponse(
        {
            "id": cliente.id,
            "nombres": cliente.nombres,
            "apellidos": cliente.apellidos or "",
            "ci_nit": cliente.ci_nit or "",
            "telefono": cliente.telefono or "",
            "direccion": cliente.direccion or "",
            "descripcion": cliente.descripcion or "",
            "latitud": str(cliente.latitud) if cliente.latitud is not None else "",
            "longitud": str(cliente.longitud) if cliente.longitud is not None else "",
            "foto_url": cliente.foto_tienda.url if cliente.foto_tienda else "",
            "activo": cliente.activo,
            "creado_por": cliente.creado_por.get_full_name() or cliente.creado_por.username if cliente.creado_por else "Sistema",
            "rol_creador": rol_creador,
            "fecha_creacion": cliente.fecha_creacion.strftime("%d/%m/%Y %H:%M"),
        }
    )


@role_required("administrador", "supervisor", "preventista")
@require_http_methods(["POST"])
def editar_cliente(request, id: int):
    cliente = get_object_or_404(_clientes_qs_para_usuario(request.user), id=id)
    nombres = (request.POST.get("nombres") or "").strip()
    apellidos = (request.POST.get("apellidos") or "").strip()
    ci_nit = (request.POST.get("ci_nit") or "").strip()
    telefono = (request.POST.get("telefono") or "").strip()
    direccion = (request.POST.get("direccion") or "").strip()
    descripcion = (request.POST.get("descripcion") or "").strip()
    latitud = (request.POST.get("latitud") or "").strip()
    longitud = (request.POST.get("longitud") or "").strip()
    foto_tienda = request.FILES.get("foto_tienda")
    activo = request.POST.get("activo") == "on"

    if not nombres:
        messages.error(request, "El nombre es obligatorio")
        return redirect("listar_clientes")

    cliente.nombres = nombres
    cliente.apellidos = apellidos or None
    cliente.ci_nit = ci_nit or None
    cliente.telefono = telefono or None
    cliente.direccion = direccion or None
    cliente.descripcion = descripcion or None
    cliente.latitud = latitud or None
    cliente.longitud = longitud or None
    if foto_tienda:
        cliente.foto_tienda = foto_tienda
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
