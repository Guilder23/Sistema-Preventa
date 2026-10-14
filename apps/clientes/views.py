from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from decimal import Decimal
from collections import defaultdict

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.core.paginator import Paginator

from apps.usuarios.decorators import role_required

from .access import clientes_visibles_para_usuario
from .models import Cliente, TransferenciaCliente
from apps.pedidos.views import _formatear_hora_local_pedido


def _clientes_qs_para_usuario(user):
    return clientes_visibles_para_usuario(user)


def _vendedor_ids(clientes_base):
    asignados = set(
        clientes_base.exclude(preventista_asignado__isnull=True)
        .values_list("preventista_asignado_id", flat=True)
    )
    anteriores = set(
        clientes_base.filter(preventista_asignado__isnull=True)
        .exclude(creado_por__isnull=True)
        .values_list("creado_por_id", flat=True)
    )
    return asignados | anteriores


def _nombre_usuario(usuario):
    if not usuario:
        return "Sin asignar"
    return (usuario.get_full_name() or usuario.username)[:150]


@role_required("administrador")
@require_http_methods(["GET", "POST"])
def transferir_clientes(request):
    preventistas = User.objects.filter(
        is_active=True,
        perfil__rol="preventista",
        perfil__activo=True,
    ).order_by("first_name", "last_name", "username")

    if request.method == "POST":
        ids_raw = request.POST.getlist("cliente_ids")
        try:
            cliente_ids = list(dict.fromkeys(int(value) for value in ids_raw))
            origen_id = int(request.POST.get("preventista_origen", ""))
            destino_id = int(request.POST.get("preventista_destino", ""))
        except (TypeError, ValueError):
            messages.error(request, "Selecciona un preventista de origen y otro de destino válidos.")
            return redirect("transferir_clientes")

        if not cliente_ids:
            messages.error(request, "Selecciona al menos un cliente para transferir.")
            return redirect(f"{reverse('transferir_clientes')}?origen={origen_id}")

        origen = get_object_or_404(preventistas, pk=origen_id)
        destino = get_object_or_404(preventistas, pk=destino_id)
        if origen.pk == destino.pk:
            messages.error(request, "El preventista de origen y destino deben ser diferentes.")
            return redirect(f"{reverse('transferir_clientes')}?origen={origen.pk}")

        with transaction.atomic():
            clientes_seleccionados = list(
                Cliente.objects.select_for_update()
                .filter(pk__in=cliente_ids)
                .order_by("pk")
            )
            if len(clientes_seleccionados) != len(cliente_ids):
                messages.error(request, "Uno o más clientes ya no existen. No se realizó ningún cambio.")
                return redirect(f"{reverse('transferir_clientes')}?origen={origen.pk}")

            pertenecen_al_origen = all(
                cliente.preventista_asignado_id == origen.pk
                or (
                    cliente.preventista_asignado_id is None
                    and cliente.creado_por_id == origen.pk
                )
                for cliente in clientes_seleccionados
            )
            if not pertenecen_al_origen:
                messages.error(
                    request,
                    "La cartera cambió mientras preparabas el traspaso. No se realizó ningún cambio; revisa de nuevo los clientes del origen.",
                )
                return redirect(f"{reverse('transferir_clientes')}?origen={origen.pk}")

            transferidos = 0
            for cliente in clientes_seleccionados:
                anterior = cliente.preventista_asignado or cliente.creado_por
                if anterior and anterior.pk == destino.pk:
                    continue

                TransferenciaCliente.objects.create(
                    cliente=cliente,
                    cliente_nombre=str(cliente)[:320],
                    responsable_anterior=anterior,
                    responsable_anterior_nombre=_nombre_usuario(anterior),
                    responsable_nuevo=destino,
                    responsable_nuevo_nombre=_nombre_usuario(destino),
                    realizado_por=request.user,
                    realizado_por_nombre=_nombre_usuario(request.user),
                )
                cliente.preventista_asignado = destino
                cliente.save(update_fields=["preventista_asignado", "fecha_actualizacion"])
                transferidos += 1

        if transferidos:
            messages.success(
                request,
                f"Se transfirieron {transferidos} cliente(s) a {_nombre_usuario(destino)}.",
            )
        else:
            messages.info(request, "Los clientes seleccionados ya pertenecían a ese preventista.")
        return redirect(f"{reverse('transferir_clientes')}?origen={origen.pk}")

    q = (request.GET.get("q") or "").strip()
    origen_raw = (request.GET.get("origen") or "").strip()
    origen = None
    if origen_raw:
        try:
            origen_id = int(origen_raw)
        except ValueError:
            origen_id = None
        if origen_id is not None:
            origen = preventistas.filter(pk=origen_id).first()

    clientes_qs = Cliente.objects.select_related("creado_por", "preventista_asignado").all()
    if origen:
        clientes_qs = clientes_qs.filter(
            Q(preventista_asignado_id=origen.pk)
            | Q(preventista_asignado__isnull=True, creado_por_id=origen.pk)
        )
    else:
        clientes_qs = clientes_qs.none()

    if q:
        clientes_qs = clientes_qs.filter(
            Q(nombres__icontains=q)
            | Q(apellidos__icontains=q)
            | Q(ci_nit__icontains=q)
            | Q(telefono__icontains=q)
        )

    paginator = Paginator(clientes_qs.order_by("nombres", "apellidos", "pk"), 100)
    page_obj = paginator.get_page(request.GET.get("page", 1))
    for cliente in page_obj.object_list:
        cliente.responsable_actual = cliente.preventista_asignado or cliente.creado_por

    return render(
        request,
        "transferencias/transferir.html",
        {
            "page_obj": page_obj,
            "clientes": page_obj.object_list,
            "paginator": paginator,
            "q": q,
            "origen_id": origen.pk if origen else "",
            "origen": origen,
            "preventistas_origen": preventistas,
            "preventistas_destino": (
                preventistas.exclude(pk=origen.pk) if origen else preventistas
            ),
            "transferencias": TransferenciaCliente.objects.select_related(
                "responsable_anterior", "responsable_nuevo", "realizado_por"
            )[:50],
        },
    )


@role_required("administrador", "supervisor", "preventista")
def listar_clientes(request):
    q = (request.GET.get("q") or "").strip()
    estado = (request.GET.get("estado") or "").strip().lower()
    vendedor_raw = (request.GET.get("vendedor") or "").strip()

    clientes_base = _clientes_qs_para_usuario(request.user)

    # Vendedores disponibles dentro del alcance del usuario
    vendedor_ids = _vendedor_ids(clientes_base)
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

    clientes = clientes_base.select_related("creado_por", "preventista_asignado").annotate(
        tiene_pedidos=Count("pedidos")
    ).order_by("-fecha_creacion")
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
        clientes = clientes.filter(
            Q(preventista_asignado_id=vendedor_id)
            | Q(preventista_asignado__isnull=True, creado_por_id=vendedor_id)
        )

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
    vendedor_ids = _vendedor_ids(clientes_base)
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
    vendedor_ids = _vendedor_ids(clientes_base)

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
        qs = qs.filter(
            Q(preventista_asignado_id=vendedor_id)
            | Q(preventista_asignado__isnull=True, creado_por_id=vendedor_id)
        )
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
                "foto_url": c.foto_tienda.url if c.foto_tienda else "",
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

    # Guardar la fecha de creación con hora de Bolivia explícita
    from django.utils import timezone as dj_timezone
    from zoneinfo import ZoneInfo

    cliente_data = {
        "nombres": nombres,
        "apellidos": apellidos or None,
        "ci_nit": ci_nit or None,
        "telefono": telefono or None,
        "direccion": direccion or None,
        "descripcion": descripcion or None,
        "latitud": latitud or None,
        "longitud": longitud or None,
        "creado_por": request.user,
        "preventista_asignado": (
            request.user
            if getattr(getattr(request.user, "perfil", None), "rol", None) == "preventista"
            else None
        ),
    }
    if foto_tienda:
        cliente_data["foto_tienda"] = foto_tienda

    try:
        cliente = Cliente.objects.create(**cliente_data)
    except Exception as exc:
        if foto_tienda:
            logging.getLogger(__name__).exception("Error al crear cliente con imagen de la tienda")
            messages.error(
                request,
                "No se pudo guardar la imagen de la tienda. Verifica que el archivo sea una imagen válida e inténtalo nuevamente.",
            )
            return redirect("listar_clientes")
        raise
    try:
        # Asegurar que la fecha_creacion (DateTimeField auto_now_add) tenga tzinfo correcto
        tz = ZoneInfo("America/La_Paz")
        if hasattr(cliente, "fecha_creacion") and cliente.fecha_creacion:
            dt = cliente.fecha_creacion
            if getattr(dt, "tzinfo", None) is None:
                dt = dt.replace(tzinfo=tz)
            cliente.fecha_creacion = dt.astimezone(tz)
            cliente.save(update_fields=["fecha_creacion"])
    except Exception:
        # No bloquear en fallo; la creación ya se hizo
        pass
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
            "preventista_asignado": (
                _nombre_usuario(cliente.preventista_asignado)
                if cliente.preventista_asignado
                else "Sin asignar"
            ),
            "rol_creador": rol_creador,
            "fecha_creacion": _formatear_hora_local_pedido(cliente.fecha_creacion),
        }
    )


@role_required("administrador", "supervisor", "preventista")
def historial_pedidos_cliente(request, id: int):
    cliente = get_object_or_404(_clientes_qs_para_usuario(request.user), id=id)

    from apps.pedidos.models import DevolucionItem, Pedido

    pedidos_qs = (
        Pedido.objects.filter(cliente=cliente)
        .select_related("preventista", "registrado_por")
        .prefetch_related("detalles__producto")
        .order_by("-fecha")
    )

    resumen = pedidos_qs.aggregate(total_pedidos=Count("id"), total_bruto=Sum("total"))
    estado_counts = {
        item["estado"]: item["total"]
        for item in pedidos_qs.values("estado").annotate(total=Count("id"))
    }

    pedidos = list(pedidos_qs)
    detalle_ids = [
        detalle.id
        for pedido in pedidos
        for detalle in pedido.detalles.all()
    ]

    devueltos_por_detalle = defaultdict(int)
    if detalle_ids:
        devoluciones = DevolucionItem.objects.filter(
            devolucion__pedido_id__in=[pedido.id for pedido in pedidos],
            detalle_pedido_id__in=detalle_ids,
        ).select_related("detalle_pedido")
        for item in devoluciones:
            devueltos_por_detalle[item.detalle_pedido_id] += int(item.cantidad_devuelta or 0)

    pedidos_data = []
    total_devuelto = Decimal("0.00")

    for pedido in pedidos:
        detalles_data = []
        pedido_devuelto = Decimal("0.00")

        for detalle in pedido.detalles.all():
            cantidad_devuelta = int(devueltos_por_detalle.get(detalle.id, 0))
            monto_devuelto = (detalle.precio_unitario or Decimal("0.00")) * Decimal(cantidad_devuelta)
            subtotal_neto = (detalle.subtotal or Decimal("0.00")) - monto_devuelto
            pedido_devuelto += monto_devuelto

            detalles_data.append(
                {
                    "producto": detalle.producto.nombre,
                    "cantidad": detalle.cantidad,
                    "cantidad_devuelta": cantidad_devuelta,
                    "precio_unitario": f"{(detalle.precio_unitario or Decimal('0.00')):.2f}",
                    "subtotal": f"{(detalle.subtotal or Decimal('0.00')):.2f}",
                    "subtotal_neto": f"{subtotal_neto:.2f}",
                }
            )

        total_bruto_pedido = pedido.total or Decimal("0.00")
        total_neto_pedido = total_bruto_pedido - pedido_devuelto
        total_devuelto += pedido_devuelto

        pedidos_data.append(
            {
                "id": pedido.id,
                "fecha": pedido.fecha.strftime("%d/%m/%Y %H:%M") if pedido.fecha else "",
                "fecha_entrega": (
                    pedido.fecha_entrega_estimada.strftime("%d/%m/%Y")
                    if pedido.fecha_entrega_estimada
                    else ""
                ),
                "fecha_vendido": (
                    pedido.fecha_vendido.strftime("%d/%m/%Y %H:%M")
                    if pedido.fecha_vendido
                    else ""
                ),
                "estado": pedido.estado,
                "estado_display": pedido.get_estado_display(),
                "preventista": pedido.preventista.get_full_name() or pedido.preventista.username,
                "registrado_por": (
                    (pedido.registrado_por.get_full_name() or pedido.registrado_por.username)
                    if pedido.registrado_por
                    else ""
                ),
                "total": f"{total_bruto_pedido:.2f}",
                "total_devuelto": f"{pedido_devuelto:.2f}",
                "total_neto": f"{total_neto_pedido:.2f}",
                "observacion": pedido.observacion or "",
                "detalles": detalles_data,
            }
        )

    total_bruto = resumen.get("total_bruto") or Decimal("0.00")
    total_real = total_bruto - total_devuelto

    return render(
        request,
        "clientes/historial.html",
        {
            "cliente": cliente,
            "resumen": {
                "total_pedidos": resumen.get("total_pedidos") or 0,
                "pendientes": estado_counts.get(Pedido.ESTADO_PENDIENTE, 0),
                "vendidos": estado_counts.get(Pedido.ESTADO_VENDIDO, 0),
                "no_entregados": estado_counts.get(Pedido.ESTADO_NO_ENTREGADO, 0),
                "anulados": estado_counts.get(Pedido.ESTADO_ANULADO, 0),
                "total_bruto": f"{total_bruto:.2f}",
                "total_devuelto": f"{total_devuelto:.2f}",
                "total_real": f"{total_real:.2f}",
            },
            "pedidos": pedidos_data,
        },
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


@role_required("administrador")
@require_http_methods(["POST"])
def eliminar_cliente(request, id: int):
    cliente = get_object_or_404(Cliente, id=id)
    from apps.pedidos.models import Pedido
    if Pedido.objects.filter(cliente=cliente).exists():
        messages.error(request, "No se puede eliminar el cliente porque tiene pedidos asociados")
        return redirect("listar_clientes")
    cliente.delete()
    messages.success(request, "Cliente eliminado correctamente")
    return redirect("listar_clientes")
