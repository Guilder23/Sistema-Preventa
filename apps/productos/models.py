from django.contrib.auth.models import User
from django.db import models


class Producto(models.Model):
    codigo = models.CharField(max_length=50, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True, null=True)
    foto = models.ImageField(upload_to="productos/", blank=True, null=True)

    precio_unidad = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_mayor = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    precio_caja = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    activo = models.BooleanField(default=True)
    creado_por = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Producto"
        verbose_name_plural = "Productos"
        ordering = ["nombre"]

    def __str__(self) -> str:
        return f"{self.codigo} - {self.nombre}"
