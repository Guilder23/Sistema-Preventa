from django.contrib.auth.models import User
from django.db.models import Q, QuerySet

from apps.usuarios.models import PerfilUsuario

from .models import Cliente


def clientes_visibles_para_usuario(user: User, activos: bool | None = None) -> QuerySet:
    clientes = Cliente.objects.all()
    if activos is not None:
        clientes = clientes.filter(activo=activos)

    perfil = getattr(user, "perfil", None)
    if user.is_superuser or (perfil and perfil.rol == "administrador"):
        return clientes

    if perfil and perfil.rol == "supervisor":
        preventistas_ids = list(
            PerfilUsuario.objects.filter(
                rol="preventista",
                supervisor=user,
                activo=True,
                usuario__is_active=True,
            ).values_list("usuario_id", flat=True)
        )
        usuarios_del_equipo = [user.pk, *preventistas_ids]
        return clientes.filter(
            Q(preventista_asignado=user)
            | Q(preventista_asignado_id__in=preventistas_ids)
            | Q(preventista_asignado__isnull=True, creado_por_id__in=usuarios_del_equipo)
        )

    if perfil and perfil.rol == "preventista":
        return clientes.filter(
            Q(preventista_asignado=user)
            | Q(preventista_asignado__isnull=True, creado_por=user)
        )

    return clientes.none()