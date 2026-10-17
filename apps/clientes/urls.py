from django.urls import path

from . import views


urlpatterns = [
    path("clientes/", views.listar_clientes, name="listar_clientes"),
    path("clientes/transferir/", views.transferir_clientes, name="transferir_clientes"),
    path("clientes/mapa/", views.clientes_mapa, name="clientes_mapa"),
    path("clientes/api/puntos/", views.clientes_mapa_puntos, name="clientes_mapa_puntos"),
    path("clientes/<int:id>/asignar-responsable/", views.cambiar_responsable_cliente, name="cambiar_responsable_cliente"),
    path("clientes/crear/", views.crear_cliente, name="crear_cliente"),
    path("clientes/<int:id>/obtener/", views.obtener_cliente, name="obtener_cliente"),
    path("clientes/<int:id>/historial/", views.historial_pedidos_cliente, name="historial_pedidos_cliente"),
    path("clientes/<int:id>/editar/", views.editar_cliente, name="editar_cliente"),
    path("clientes/<int:id>/bloquear/", views.bloquear_cliente, name="bloquear_cliente"),
    path("clientes/<int:id>/eliminar/", views.eliminar_cliente, name="eliminar_cliente"),
]
