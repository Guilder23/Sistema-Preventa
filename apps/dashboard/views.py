from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from django.shortcuts import render
from django.utils import timezone


@login_required
def dashboard(request):
    from apps.clientes.models import Cliente
    from apps.pedidos.models import Pedido
    from apps.productos.models import Producto

    user = request.user
    perfil = getattr(user, "perfil", None)

    # Productos: todos visibles
    total_productos = Producto.objects.filter(activo=True).count()

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

    vendidos_hoy_qs = pedidos_qs.filter(
        estado=Pedido.ESTADO_VENDIDO,
        fecha_vendido__date=hoy,
    )
    vendidos_hoy = vendidos_hoy_qs.count()
    monto_vendido_hoy = vendidos_hoy_qs.aggregate(total=Sum("total")).get("total") or 0

    total_vendidos = pedidos_qs.filter(estado=Pedido.ESTADO_VENDIDO).count()
    total_pendientes = pedidos_qs.filter(estado=Pedido.ESTADO_PENDIENTE).count()
    total_anulados = pedidos_qs.filter(estado=Pedido.ESTADO_ANULADO).count()
    total_monto = pedidos_qs.aggregate(total=Sum("total")).get("total") or 0

    pedidos_recientes = pedidos_qs.select_related("cliente", "preventista").order_by("-fecha")[:8]

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "total_productos": total_productos,
            "total_clientes": total_clientes,
            "total_pedidos": total_pedidos,
            "total_vendidos": total_vendidos,
            "total_pendientes": total_pendientes,
            "total_anulados": total_anulados,
            "total_monto": total_monto,
            "pedidos_hoy": pedidos_hoy,
            "pendientes_hoy": pendientes_hoy,
            "anulados_hoy": anulados_hoy,
            "vendidos_hoy": vendidos_hoy,
            "monto_vendido_hoy": monto_vendido_hoy,
            "pedidos_recientes": pedidos_recientes,
        },
    )


@login_required
def ayuda(request):
    return render(request, "dashboard/ayuda.html")


@login_required
def configuracion(request):
    return render(request, "dashboard/configuracion.html")
