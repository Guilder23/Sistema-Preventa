from django.contrib import admin

from .models import DevolucionItem, DevolucionPedido, DetallePedido, Pedido


class DetallePedidoInline(admin.TabularInline):
    model = DetallePedido
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "cliente", "preventista", "fecha", "estado", "total")
    list_filter = ("estado", "fecha")
    search_fields = ("cliente__nombres", "cliente__apellidos", "cliente__ci_nit")
    inlines = [DetallePedidoInline]


@admin.register(DetallePedido)
class DetallePedidoAdmin(admin.ModelAdmin):
    list_display = ("pedido", "producto", "cantidad", "precio_unitario", "subtotal")


class DevolucionItemInline(admin.TabularInline):
    model = DevolucionItem
    extra = 0


@admin.register(DevolucionPedido)
class DevolucionPedidoAdmin(admin.ModelAdmin):
    list_display = ("id", "pedido", "repartidor", "tipo", "estado_reposicion", "fecha_creacion")
    list_filter = ("tipo", "estado_reposicion", "fecha_creacion")
    search_fields = ("pedido__id", "pedido__cliente__nombres", "pedido__cliente__apellidos")
    inlines = [DevolucionItemInline]


@admin.register(DevolucionItem)
class DevolucionItemAdmin(admin.ModelAdmin):
    list_display = ("devolucion", "producto", "cantidad_devuelta", "repuesto", "fecha_reposicion")
    list_filter = ("repuesto",)
