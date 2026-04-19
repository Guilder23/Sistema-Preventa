from __future__ import annotations

import json

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

from .decorators import role_required
from .models import PerfilUsuario


def index(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "inicio/index.html")


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password = request.POST.get("password") or ""

        user = authenticate(request, username=username, password=password)
        if user is None:
            messages.error(request, "Usuario o contraseña incorrectos")
            return redirect("login")

        if not user.is_active:
            messages.error(request, "Tu usuario está bloqueado")
            return redirect("login")

        if not user.is_superuser:
            perfil = getattr(user, "perfil", None)
            if not perfil or not perfil.activo:
                messages.error(request, "Tu usuario está bloqueado")
                return redirect("login")

        login(request, user)
        return redirect("dashboard")

    return render(request, "inicio/modals/login.html")


def custom_logout(request):
    logout(request)
    messages.success(request, "Sesión cerrada exitosamente")
    return redirect("index")


@login_required
@require_http_methods(["GET", "POST"])
def mi_perfil(request):
    usuario = request.user
    perfil = getattr(usuario, "perfil", None)

    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        first_name = (request.POST.get("first_name") or "").strip()
        last_name = (request.POST.get("last_name") or "").strip()

        telefono = (request.POST.get("telefono") or "").strip()
        direccion = (request.POST.get("direccion") or "").strip()

        nueva_password = request.POST.get("password") or ""
        nueva_password2 = request.POST.get("password2") or ""
        foto = request.FILES.get("foto")

        if email and User.objects.filter(email=email).exclude(id=usuario.id).exists():
            messages.error(request, f'El correo "{email}" ya está registrado')
            return redirect("mi_perfil")

        if nueva_password or nueva_password2:
            if nueva_password != nueva_password2:
                messages.error(request, "Las contraseñas no coinciden")
                return redirect("mi_perfil")
            if len(nueva_password) < 8:
                messages.error(request, "La contraseña debe tener al menos 8 caracteres")
                return redirect("mi_perfil")

        usuario.email = email
        usuario.first_name = first_name
        usuario.last_name = last_name
        if nueva_password:
            usuario.set_password(nueva_password)
        usuario.save()

        if nueva_password:
            update_session_auth_hash(request, usuario)

        if perfil:
            perfil.telefono = telefono or None
            perfil.direccion = direccion or None
            if foto:
                perfil.foto = foto
            perfil.save()

        messages.success(request, "Perfil actualizado correctamente")
        return redirect("mi_perfil")

    return render(request, "usuarios/perfil.html", {"perfil": perfil})


@role_required("administrador")
def listar_usuarios(request):
    buscar = (request.GET.get("buscar") or "").strip()
    estado = (request.GET.get("estado") or "").strip()
    rol = (request.GET.get("rol") or "").strip()

    usuarios = User.objects.select_related("perfil").order_by("-date_joined")

    if buscar:
        usuarios = usuarios.filter(
            username__icontains=buscar
        )
    if estado == "activo":
        usuarios = usuarios.filter(is_active=True)
    elif estado == "inactivo":
        usuarios = usuarios.filter(is_active=False)

    if rol:
        usuarios = usuarios.filter(perfil__rol=rol)

    # PAGINACIÓN (igual que clientes)
    page = request.GET.get("page", 1)
    paginator = Paginator(usuarios, 10)  # 10 usuarios por página
    try:
        page_obj = paginator.page(page)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    supervisores = (
        User.objects.select_related("perfil")
        .filter(perfil__rol="supervisor", is_active=True, perfil__activo=True)
        .order_by("username")
    )

    repartidores = (
        User.objects.select_related("perfil")
        .filter(perfil__rol="repartidor", is_active=True, perfil__activo=True)
        .order_by("username")
    )

    return render(
        request,
        "usuarios/usuarios.html",
        {
            "usuarios": page_obj.object_list,
            "page_obj": page_obj,
            "paginator": paginator,
            "buscar": buscar,
            "estado": estado,
            "rol": rol,
            "supervisores": supervisores,
            "repartidores": repartidores,
            # compat con UI del proyecto guía
            "almacenes": [],
            "tiendas": [],
            "usuarios_quota_json": None,
            "plan_obj": None,
            "usuarios_total_usados": None,
            "usuarios_total_limite": None,
            "usuarios_total_restantes": None,
        },
    )


@role_required("administrador")
@require_http_methods(["POST"])
def crear_usuario(request):
    username = (request.POST.get("username") or "").strip()
    email = (request.POST.get("email") or "").strip()
    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    password = request.POST.get("password") or ""
    password2 = request.POST.get("password2") or ""
    rol = (request.POST.get("rol") or "").strip() or "preventista"
    supervisor_id = (request.POST.get("supervisor_id") or "").strip()
    repartidor_id = (request.POST.get("repartidor_id") or "").strip()
    is_active = request.POST.get("is_active") == "on"

    if not username or not email or not password or not password2 or not rol:
        messages.error(request, "Complete los campos requeridos")
        return redirect("listar_usuarios")
    if password != password2:
        messages.error(request, "Las contraseñas no coinciden")
        return redirect("listar_usuarios")
    if len(password) < 8:
        messages.error(request, "La contraseña debe tener al menos 8 caracteres")
        return redirect("listar_usuarios")
    if User.objects.filter(username=username).exists():
        messages.error(request, f'El usuario "{username}" ya existe')
        return redirect("listar_usuarios")
    if email and User.objects.filter(email=email).exists():
        messages.error(request, f'El correo "{email}" ya está registrado')
        return redirect("listar_usuarios")

    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
        is_active=is_active,
    )

    supervisor = None
    if rol == "preventista" and supervisor_id:
        supervisor = get_object_or_404(User.objects.select_related("perfil"), id=supervisor_id)
        if not getattr(supervisor, "perfil", None) or supervisor.perfil.rol != "supervisor":
            messages.error(request, "El usuario seleccionado no es Supervisor")
            user.delete()
            return redirect("listar_usuarios")

    repartidor = None
    if rol == "preventista" and repartidor_id:
        repartidor = get_object_or_404(User.objects.select_related("perfil"), id=repartidor_id)
        if not getattr(repartidor, "perfil", None) or repartidor.perfil.rol != "repartidor":
            messages.error(request, "El usuario seleccionado no es Repartidor")
            user.delete()
            return redirect("listar_usuarios")

    if rol == "preventista" and (not supervisor or not repartidor):
        messages.error(request, "Para un Preventista debes asignar un Supervisor y un Repartidor")
        user.delete()
        return redirect("listar_usuarios")

    PerfilUsuario.objects.update_or_create(
        usuario=user,
        defaults={
            "rol": rol,
            "activo": is_active,
            "supervisor": supervisor,
            "repartidor": repartidor,
            "creado_por": request.user,
        },
    )
    messages.success(request, "Usuario creado correctamente")
    return redirect("listar_usuarios")


@role_required("administrador")
def obtener_usuario(request, id: int):
    usuario = get_object_or_404(User.objects.select_related("perfil"), id=id)
    perfil = getattr(usuario, "perfil", None)

    if usuario.is_superuser and not perfil:
        rol = "administrador"
        rol_display = "Administrador"
    else:
        rol = perfil.rol if perfil else ""
        rol_display = perfil.get_rol_display() if perfil else "Sin rol"

    data = {
        "id": usuario.id,
        "username": usuario.username,
        "email": usuario.email,
        "first_name": usuario.first_name,
        "last_name": usuario.last_name,
        "nombre_completo": (usuario.get_full_name() or "").strip(),
        "rol": rol,
        "rol_display": rol_display,
        "supervisor_id": perfil.supervisor_id if perfil else None,
        "repartidor_id": perfil.repartidor_id if perfil else None,
        "supervisor_nombre": (
            (perfil.supervisor.get_full_name() or perfil.supervisor.username)
            if (perfil and perfil.supervisor)
            else None
        ),
        "repartidor_nombre": (
            (perfil.repartidor.get_full_name() or perfil.repartidor.username)
            if (perfil and perfil.repartidor)
            else None
        ),
        "is_active": usuario.is_active,
        "last_login": usuario.last_login.strftime("%d/%m/%y %H:%M") if usuario.last_login else None,
        "date_joined": usuario.date_joined.strftime("%d/%m/%y %H:%M") if usuario.date_joined else None,
        # Compat con UI del proyecto guía
        "almacen_id": None,
        "almacen_nombre": None,
        "tienda_id": None,
        "tienda_nombre": None,
        "creado_por": (
            (perfil.creado_por.get_full_name() or perfil.creado_por.username)
            if (perfil and perfil.creado_por)
            else "Sistema"
        ),
    }
    return JsonResponse(data)


@role_required("administrador")
@require_http_methods(["POST"])
def editar_usuario(request, id: int):
    usuario = get_object_or_404(User.objects.select_related("perfil"), id=id)

    email = (request.POST.get("email") or "").strip()
    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    rol = (request.POST.get("rol") or "").strip() or "preventista"
    supervisor_id = (request.POST.get("supervisor_id") or "").strip()
    repartidor_id = (request.POST.get("repartidor_id") or "").strip()
    is_active = request.POST.get("is_active") == "on"
    password = request.POST.get("password") or ""

    if email and User.objects.filter(email=email).exclude(id=usuario.id).exists():
        messages.error(request, f'El correo "{email}" ya está registrado')
        return redirect("listar_usuarios")

    usuario.email = email
    usuario.first_name = first_name
    usuario.last_name = last_name
    usuario.is_active = is_active

    if password:
        if len(password) < 8:
            messages.error(request, "La contraseña debe tener al menos 8 caracteres")
            return redirect("listar_usuarios")
        usuario.set_password(password)
    usuario.save()

    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    perfil.rol = rol
    perfil.activo = is_active

    supervisor = None
    if rol == "preventista" and supervisor_id:
        supervisor = get_object_or_404(User.objects.select_related("perfil"), id=supervisor_id)
        if not getattr(supervisor, "perfil", None) or supervisor.perfil.rol != "supervisor":
            messages.error(request, "El usuario seleccionado no es Supervisor")
            return redirect("listar_usuarios")

    repartidor = None
    if rol == "preventista" and repartidor_id:
        repartidor = get_object_or_404(User.objects.select_related("perfil"), id=repartidor_id)
        if not getattr(repartidor, "perfil", None) or repartidor.perfil.rol != "repartidor":
            messages.error(request, "El usuario seleccionado no es Repartidor")
            return redirect("listar_usuarios")

    if rol == "preventista" and (not supervisor or not repartidor):
        messages.error(request, "Para un Preventista debes asignar un Supervisor y un Repartidor")
        return redirect("listar_usuarios")
    perfil.supervisor = supervisor
    perfil.repartidor = repartidor
    perfil.save()

    if password and usuario.id == request.user.id:
        update_session_auth_hash(request, usuario)

    messages.success(request, "Usuario actualizado correctamente")
    return redirect("listar_usuarios")


@role_required("administrador")
@require_http_methods(["POST"])
def bloquear_usuario(request, id: int):
    usuario = get_object_or_404(User.objects.select_related("perfil"), id=id)

    if usuario.is_superuser:
        messages.error(request, "No se puede bloquear un superusuario")
        return redirect("listar_usuarios")

    nuevo_estado = not usuario.is_active
    usuario.is_active = nuevo_estado
    usuario.save(update_fields=["is_active"])

    perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
    perfil.activo = nuevo_estado
    perfil.save(update_fields=["activo"])

    messages.success(
        request,
        "Usuario activado" if nuevo_estado else "Usuario bloqueado",
    )
    return redirect("listar_usuarios")
