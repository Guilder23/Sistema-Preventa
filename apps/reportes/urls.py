from django.urls import path

from . import views


urlpatterns = [
    path("reportes/", views.reportes_inicio, name="reportes_inicio"),
    path("reportes/pedidos/pdf/", views.pedidos_pdf, name="reporte_pedidos_pdf"),
    path("reportes/pedidos/<int:id>/ticket/", views.pedido_ticket, name="reporte_pedido_ticket"),
    path("reportes/pedidos/<int:id>/ticket/marcar-impreso/", views.marcar_ticket_impreso, name="reporte_pedido_ticket_impreso"),
    path("reportes/pedidos/<int:id>/ticket/whatsapp/", views.compartir_ticket_whatsapp, name="reporte_pedido_ticket_whatsapp"),
    path("reportes/pedidos/<int:id>/pdf/", views.pedido_pdf, name="reporte_pedido_pdf"),
]
