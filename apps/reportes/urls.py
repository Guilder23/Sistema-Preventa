from django.urls import path

from . import views


urlpatterns = [
    path("reportes/", views.reportes_inicio, name="reportes_inicio"),
    path("reportes/pedidos/<int:id>/pdf/", views.pedido_pdf, name="reporte_pedido_pdf"),
]
