from django.urls import path

from . import views


urlpatterns = [
    path("pedidos/", views.listar_pedidos, name="listar_pedidos"),
    path("devoluciones/", views.listar_devoluciones, name="listar_devoluciones"),
    path("devoluciones/<int:id>/obtener/", views.obtener_devolucion, name="obtener_devolucion"),
    path("devoluciones/<int:id>/resumen-reponer/", views.resumen_reponer_devolucion, name="resumen_reponer_devolucion"),
    path("devoluciones/<int:id>/reponer/", views.reponer_devolucion, name="reponer_devolucion"),
    path("devoluciones/item/<int:id>/reponer/", views.reponer_devolucion_item, name="reponer_devolucion_item"),
    path("devoluciones/resumen-reponer-todo/", views.resumen_reponer_todo_devoluciones, name="resumen_reponer_todo_devoluciones"),
    path("devoluciones/reponer-todo/", views.reponer_todo_devoluciones, name="reponer_todo_devoluciones"),
    path("pedidos/mapa/", views.pedidos_mapa, name="pedidos_mapa"),
    path("pedidos/api/puntos/", views.pedidos_mapa_puntos, name="pedidos_mapa_puntos"),
    path("pedidos/crear/", views.crear_pedido, name="crear_pedido"),
    path("pedidos/<int:id>/obtener/", views.obtener_pedido, name="obtener_pedido"),
    path("pedidos/<int:id>/editar/", views.editar_pedido, name="editar_pedido"),
    path("pedidos/<int:id>/entrega/", views.registrar_entrega, name="registrar_entrega_pedido"),
    path("pedidos/<int:id>/vendido/", views.marcar_vendido, name="marcar_pedido_vendido"),
    path("pedidos/<int:id>/anular/", views.anular_pedido, name="anular_pedido"),
]
