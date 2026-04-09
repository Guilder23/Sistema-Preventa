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

    ESTADOS = (
        (ESTADO_PENDIENTE, "Pendiente"),
        (ESTADO_VENDIDO, "Vendido"),
        (ESTADO_ANULADO, "Anulado"),
    )

    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="pedidos")
    preventista = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos"
    )
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default=ESTADO_PENDIENTE)
    fecha_vendido = models.DateTimeField(blank=True, null=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    observacion = models.TextField(blank=True, null=True)

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
