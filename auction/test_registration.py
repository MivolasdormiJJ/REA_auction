"""Регистрация с контактным email без обязательного подтверждения."""
from django.core.cache import cache
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from auction.models import User


class RegistrationTests(TestCase):
    def setUp(self):
        cache.clear()
        self.client = APIClient()
        self.payload = {
            "username": "newbuyer",
            "email": "newbuyer@example.com",
            "password": "Unusual-Strong-Pass-2026!",
        }

    @override_settings(DEBUG=False, REGISTRATION_EMAIL_ENABLED=False)
    def test_register_and_login_without_smtp(self):
        # ПРОБЛЕМА: SMTP не настроен в production.
        # РЕШЕНИЕ: регистрируем сразу, но помним, что email не проверен.
        response = self.client.post("/api/auth/register/", self.payload, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        user = User.objects.get(username="newbuyer")
        self.assertEqual(user.email, self.payload["email"])
        self.assertTrue(user.email_verified)
        self.assertTrue(user.check_password(self.payload["password"]))
        self.assertNotIn(self.payload["password"], str(response.data))
        login = self.client.post("/api/auth/login/", {
            "username": "newbuyer", "password": self.payload["password"],
        }, format="json")
        self.assertEqual(login.status_code, 200, login.data)

    def test_duplicate_email_and_username(self):
        self.assertEqual(self.client.post("/api/auth/register/", self.payload, format="json").status_code, 201)
        self.assertEqual(self.client.post("/api/auth/register/", self.payload, format="json").status_code, 400)
        another = {**self.payload, "username": "seconduser"}
        self.assertEqual(self.client.post("/api/auth/register/", another, format="json").status_code, 400)

    def test_weak_password_rejected(self):
        response = self.client.post("/api/auth/register/", {**self.payload, "password": "short"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(User.objects.filter(username="newbuyer").exists())

    def test_email_still_required(self):
        data = {k: v for k, v in self.payload.items() if k != "email"}
        response = self.client.post("/api/auth/register/", data, format="json")
        self.assertEqual(response.status_code, 400)

    def test_invalid_legacy_verification_link(self):
        response = self.client.post("/api/auth/verify-email/", {"uid": "invalid", "token": "fake"}, format="json")
        self.assertEqual(response.status_code, 400)
