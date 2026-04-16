from django.urls import path

from . import views


urlpatterns = [
    path("productos/", views.listar_productos, name="listar_productos"),
    path("productos/crear/", views.crear_producto, name="crear_producto"),
    path("productos/<int:id>/obtener/", views.obtener_producto, name="obtener_producto"),
    path("productos/<int:id>/inventario/", views.obtener_inventario_producto, name="obtener_inventario_producto"),
    path("productos/<int:id>/inventario/ajustar/", views.ajustar_inventario_producto, name="ajustar_inventario_producto"),
    path("productos/<int:id>/editar/", views.editar_producto, name="editar_producto"),
    path("productos/<int:id>/bloquear/", views.bloquear_producto, name="bloquear_producto"),
]
