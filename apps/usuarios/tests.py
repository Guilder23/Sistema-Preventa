from unittest.mock import patch

from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core import mail
from django.test import TestCase
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


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
