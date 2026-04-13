from django.contrib.auth.models import User
from django.db import models


class PerfilUsuario(models.Model):
    ROLES = (
        ("administrador", "Administrador"),
        ("supervisor", "Supervisor"),
        ("repartidor", "Repartidor"),
        ("preventista", "Preventista"),
    )

    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    rol = models.CharField(max_length=20, choices=ROLES, default="preventista")

    # Relación jerárquica: un Supervisor puede tener varios Preventistas.
    supervisor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preventistas_asignados",
    )

    repartidor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="preventistas_asignados_como_repartidor",
    )

    creado_por = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="perfiles_usuario_creados",
    )

    telefono = models.CharField(max_length=30, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    foto = models.ImageField(upload_to="usuarios/perfiles/", blank=True, null=True)

    activo = models.BooleanField(default=True)

    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"
        ordering = ["-fecha_creacion"]

    def __str__(self) -> str:
        return f"{self.usuario.username} - {self.get_rol_display()}"
