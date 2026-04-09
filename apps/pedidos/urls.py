from django.urls import path

from . import views


urlpatterns = [
    path("pedidos/", views.listar_pedidos, name="listar_pedidos"),
    path("pedidos/crear/", views.crear_pedido, name="crear_pedido"),
    path("pedidos/<int:id>/obtener/", views.obtener_pedido, name="obtener_pedido"),
    path("pedidos/<int:id>/anular/", views.anular_pedido, name="anular_pedido"),
]
