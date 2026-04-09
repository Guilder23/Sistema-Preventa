from django.apps import AppConfig
from django.db import connection
from django.db.utils import OperationalError, ProgrammingError


class UsuariosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.usuarios"

    def ready(self):
        from . import signals  # noqa: F401

        try:
            if "auth_user" not in connection.introspection.table_names():
                return
        except (OperationalError, ProgrammingError):
            return

        from django.contrib.auth.models import User

        username = "admin"
        email = "admin@gmail.com"
        password = "admin"

        user, created = User.objects.get_or_create(
            username=username,
            defaults={"email": email},
        )
        if created:
            user.is_staff = True
            user.is_superuser = True
            user.set_password(password)
            user.save()
            return

        updated = False
        if user.email != email:
            user.email = email
            updated = True
        if not user.is_staff:
            user.is_staff = True
            updated = True
        if not user.is_superuser:
            user.is_superuser = True
            updated = True
        if updated:
            user.save()
