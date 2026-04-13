from django.contrib import admin

from .models import MovimientoInventario, Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "precio_unidad", "activo", "fecha_creacion")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    list_display = (
        "producto",
        "tipo",
        "cantidad",
        "stock_anterior",
        "stock_nuevo",
        "usuario",
        "fecha",
    )
    list_filter = ("tipo", "fecha")
    search_fields = ("producto__codigo", "producto__nombre", "motivo")
