from django.contrib import admin

from .models import Cliente


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("nombres", "apellidos", "telefono", "activo", "fecha_creacion")
    list_filter = ("activo",)
    search_fields = ("nombres", "apellidos", "ci_nit", "telefono")
