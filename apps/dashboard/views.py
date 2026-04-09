from django.contrib.auth.decorators import login_required
from django.shortcuts import render


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

    pedidos_recientes = pedidos_qs.select_related("cliente", "preventista").order_by("-fecha")[:8]

    return render(
        request,
        "dashboard/dashboard.html",
        {
            "total_productos": total_productos,
            "total_clientes": total_clientes,
            "total_pedidos": total_pedidos,
            "pedidos_recientes": pedidos_recientes,
        },
    )


@login_required
def ayuda(request):
    return render(request, "dashboard/ayuda.html")


@login_required
def configuracion(request):
    return render(request, "dashboard/configuracion.html")
