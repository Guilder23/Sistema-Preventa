from django.urls import path

from . import views


urlpatterns = [
    path("clientes/", views.listar_clientes, name="listar_clientes"),
    path("clientes/crear/", views.crear_cliente, name="crear_cliente"),
    path("clientes/<int:id>/obtener/", views.obtener_cliente, name="obtener_cliente"),
    path("clientes/<int:id>/editar/", views.editar_cliente, name="editar_cliente"),
    path("clientes/<int:id>/bloquear/", views.bloquear_cliente, name="bloquear_cliente"),
]
