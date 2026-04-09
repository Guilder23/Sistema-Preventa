from django.contrib import admin

from .models import Producto


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "precio_unidad", "activo", "fecha_creacion")
    list_filter = ("activo",)
    search_fields = ("codigo", "nombre")
