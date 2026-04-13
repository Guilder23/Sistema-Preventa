from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models

from apps.clientes.models import Cliente
from apps.productos.models import Producto


class Pedido(models.Model):
    ESTADO_PENDIENTE = "pendiente"
    ESTADO_ANULADO = "anulado"
    ESTADO_VENDIDO = "vendido"
    ESTADO_NO_ENTREGADO = "no_entregado"

    ESTADOS = (
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_VENDIDO, "Vendido"),
        (ESTADO_NO_ENTREGADO, "No entregado"),
        (ESTADO_ANULADO, "Anulado"),
    )

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    preventista = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos"
    )
    registrado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="pedidos_registrados",
        blank=True,
        null=True,
    )
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    fecha_vendido = models.DateTimeField(blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    observacion = models.TextField(blank=True, null=True)
    ticket_impreso = models.BooleanField(default=False)
    ticket_compartido = models.BooleanField(default=False)

    class Meta:
        ordering = ["-fecha"]

    def __str__(self) -> str:
        return f"Pedido #{self.id} - {self.cliente}"

    def recalcular_total(self, save: bool = True) -> Decimal:
        total = Decimal("0.00")
        for det in self.detalles.all():
            total += det.subtotal
        self.total = total
        if save:
            self.save(update_fields=["total"])
        return total


class DetallePedido(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name="detalles"
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad = models.PositiveIntegerField()
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.producto} x{self.cantidad}"


class DevolucionPedido(models.Model):
    TIPO_PARCIAL = "parcial"
    TIPO_NO_ENTREGADO = "no_entregado"

    TIPOS = (
        (TIPO_PARCIAL, "Entrega parcial"),
        (TIPO_NO_ENTREGADO, "No entregado"),
    )

    ESTADO_PENDIENTE = "pendiente"
    ESTADO_PARCIAL = "parcial"
    ESTADO_REPUESTO = "repuesto"

    ESTADOS_REPOSICION = (
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_PARCIAL, "Parcial"),
        (ESTADO_REPUESTO, "Repuesto"),
    )

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="devoluciones")
    repartidor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="devoluciones_registradas",
    )
    tipo = models.CharField(max_length=20, choices=TIPOS)
    motivo_general = models.TextField(blank=True, null=True)
    estado_reposicion = models.CharField(
        max_length=20,
        choices=ESTADOS_REPOSICION,
        default=ESTADO_PENDIENTE,
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha_creacion"]

    def __str__(self) -> str:
        return f"Devolucion #{self.id} - Pedido #{self.pedido_id}"

    def actualizar_estado_reposicion(self, save: bool = True) -> str:
        items = list(self.items.all())
        if not items:
            nuevo = self.ESTADO_PENDIENTE
        elif all(it.repuesto for it in items):
            nuevo = self.ESTADO_REPUESTO
        elif any(it.repuesto for it in items):
            nuevo = self.ESTADO_PARCIAL
        else:
            nuevo = self.ESTADO_PENDIENTE

        self.estado_reposicion = nuevo
        if save:
            self.save(update_fields=["estado_reposicion"])
        return nuevo


class DevolucionItem(models.Model):
    devolucion = models.ForeignKey(
        DevolucionPedido,
        on_delete=models.CASCADE,
        related_name="items",
    )
    detalle_pedido = models.ForeignKey(
        DetallePedido,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devoluciones",
    )
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT)
    cantidad_devuelta = models.PositiveIntegerField(default=0)
    motivo = models.TextField(blank=True, null=True)
    repuesto = models.BooleanField(default=False)
    fecha_reposicion = models.DateTimeField(blank=True, null=True)
    repuesto_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="devoluciones_repuestas",
    )

    class Meta:
        ordering = ["id"]

    def __str__(self) -> str:
        return f"{self.producto} devuelto x{self.cantidad_devuelta}"
