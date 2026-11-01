"""Проверки регистрации через веб и активации аккаунта."""
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from django.core import mail
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from auction.models import User


@override_settings(
    DEBUG=True,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.payload = {
            "username": "newbuyer",
            "email": "newbuyer@example.com",
            "password": "Unusual-Strong-Pass-2026!",
        }

    def test_registration_needs_email_confirmation(self):
        response = self.client.post("/api/auth/register/", self.payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username="newbuyer")
        self.assertFalse(user.email_verified)
        self.assertTrue(user.check_password(self.payload["password"]))
        self.assertNotIn(self.payload["password"], str(response.data))
        self.assertEqual(len(mail.outbox), 1)

        # Пока email не подтверждён, система не пускает к торгам.
        login = self.client.post("/api/auth/login/", {
            "username": "newbuyer",
            "password": self.payload["password"],
        }, format="json")
        self.assertEqual(login.status_code, 403)

        email_text = mail.outbox[0].body
        confirmation_url = next(part for part in email_text.split() if "verify-email?" in part)
        params = parse_qs(urlparse(confirmation_url).query)
        verified = self.client.post("/api/auth/verify-email/", {
            "uid": params["uid"][0],
            "token": params["token"][0],
        }, format="json")
        self.assertEqual(verified.status_code, 200, verified.data)
        user.refresh_from_db()
        self.assertTrue(user.email_verified)
        login = self.client.post("/api/auth/login/", {
            "username": "newbuyer",
            "password": self.payload["password"],
        }, format="json")
        self.assertEqual(login.status_code, 200, login.data)

    def test_duplicate_email_and_username(self):
        self.assertEqual(self.client.post("/api/auth/register/", self.payload, format="json").status_code, 201)
        duplicate = self.client.post("/api/auth/register/", self.payload, format="json")
        self.assertEqual(duplicate.status_code, 400)
        modified = {**self.payload, "username": "seconduser"}
        self.assertEqual(self.client.post("/api/auth/register/", modified, format="json").status_code, 400)

    def test_short_password_rejected(self):
        response = self.client.post("/api/auth/register/", {**self.payload, "password": "short"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="newbuyer").exists())

    def test_invalid_confirmation_rejected(self):
        response = self.client.post("/api/auth/verify-email/", {"uid": "invalid", "token": "fake"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_mail_error_rolls_back_registration(self):
        with patch("auction.views.send_mail", side_effect=OSError("SMTP unavailable")):
            response = self.client.post("/api/auth/register/", self.payload, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(User.objects.filter(username="newbuyer").exists())


@override_settings(DEBUG=False, REGISTRATION_EMAIL_ENABLED=False)
class RegistrationDisabledTests(TestCase):
    def test_no_smtp_no_registration(self):
        cache.clear()
        response = APIClient().post("/api/auth/register/", {
            "username": "someone",
            "email": "someone@example.com",
            "password": "Unusual-Strong-Pass-2026!",
        }, format="json")
        self.assertEqual(response.status_code, 503)
        self.assertFalse(User.objects.filter(username="someone").exists())
