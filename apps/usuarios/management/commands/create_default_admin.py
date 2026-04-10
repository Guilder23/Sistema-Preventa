import os

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create a default admin user if none exists"

    def handle(self, *args, **options):
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write(self.style.NOTICE("Superuser already exists"))
            return

        username = os.getenv("ADMIN_USERNAME", "admin")
        email = os.getenv("ADMIN_EMAIL", "admin@example.com")
        password = os.getenv("ADMIN_PASSWORD", "admin")

        user = User.objects.create_user(username=username, email=email, password=password)
        user.is_staff = True
        user.is_superuser = True
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Created default admin user: {username} ({email})"
            )
        )
