import importlib
import os
from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


class AllowedHostsSettingsTests(TestCase):
    def test_public_ip_is_allowed_even_when_env_overrides_hosts(self):
        import sistemaPreventa.settings as settings_module

        with patch.dict(os.environ, {"ALLOWED_HOSTS": "localhost,127.0.0.1"}, clear=False):
            reloaded_module = importlib.reload(settings_module)

        self.assertIn("187.127.45.61", reloaded_module.ALLOWED_HOSTS)


class PasswordResetFlowTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="oldpassword123",
        )

    def test_password_reset_request_sends_email(self):
        response = self.client.post(reverse("recuperar_password"), {"email": "test@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "te hemos enviado")
        self.assertEqual(len(mail.outbox), 1)

    def test_password_reset_confirm_changes_password(self):
        uid = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(
            reverse("recuperar_password_confirmar", args=[uid, token]),
            {
                "new_password": "NuevaClave123",
                "confirm_password": "NuevaClave123",
            },
        )

        self.assertRedirects(response, reverse("recuperar_password_completado"))
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NuevaClave123"))

    def test_password_reset_request_handles_smtp_error(self):
        with patch("apps.usuarios.views.send_mail", side_effect=Exception("smtp error")):
            response = self.client.post(reverse("recuperar_password"), {"email": "test@example.com"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No pudimos enviar")
