from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect


def role_required(*roles: str):
    """Restringe una vista a roles del PerfilUsuario.

    - Superuser siempre pasa.
    - Si el perfil está inactivo, se fuerza logout en la vista de logout.
    """

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            user = request.user
            if user.is_superuser:
                return view_func(request, *args, **kwargs)

            perfil = getattr(user, "perfil", None)
            if not perfil or not perfil.activo or not user.is_active:
                messages.error(request, "Tu usuario está bloqueado o sin perfil.")
                return redirect("logout")

            if roles and perfil.rol not in roles:
                messages.error(request, "No tienes permisos para acceder a esta sección.")
                return redirect("dashboard")

            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
