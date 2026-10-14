from django.contrib.auth.models import User
from django.db import models
from django.conf import settings


class Cliente(models.Model):
    nombres = models.CharField(max_length=150)
    apellidos = models.CharField(max_length=150, blank=True, null=True)
    ci_nit = models.CharField(max_length=50, blank=True, null=True)
    telefono = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)

    descripcion = models.TextField(blank=True, null=True)

    foto_tienda = models.ImageField(upload_to="clientes/tiendas/", blank=True, null=True)

    latitud = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)
    longitud = models.DecimalField(max_digits=10, decimal_places=7, blank=True, null=True)

    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    preventista_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="clientes_asignados",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ["nombres", "apellidos"]

    def __str__(self) -> str:
        nombre = f"{self.nombres} {self.apellidos or ''}".strip()
        return nombre


class TransferenciaCliente(models.Model):
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transferencias",
    )
    cliente_nombre = models.CharField(max_length=320)
    responsable_anterior = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transferencias_clientes_salientes",
    )
    responsable_anterior_nombre = models.CharField(max_length=150, blank=True)
    responsable_nuevo = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transferencias_clientes_entrantes",
    )
    responsable_nuevo_nombre = models.CharField(max_length=150)
    realizado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transferencias_clientes_realizadas",
    )
    realizado_por_nombre = models.CharField(max_length=150, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha", "-id"]
        verbose_name = "Transferencia de cliente"
        verbose_name_plural = "Transferencias de clientes"
