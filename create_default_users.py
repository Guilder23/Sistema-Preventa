import os

import django


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "sistemaPreventa.settings")
    django.setup()

    from django.contrib.auth.models import User

    if User.objects.filter(is_superuser=True).exists():
        return 0

    username = os.getenv("ADMIN_USERNAME", "admin")
    email = os.getenv("ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("ADMIN_PASSWORD", "admin")

    user = User.objects.create_user(username=username, email=email, password=password)
    user.is_staff = True
    user.is_superuser = True
    user.save()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
