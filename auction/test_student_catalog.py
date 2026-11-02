"""Tests for public student demo content and category choice."""
from django.core.management import call_command
from django.test import TestCase

from auction.models import Auction, Bid, Category, User


class StudentCatalogSeedTests(TestCase):
    def test_categories_and_public_examples(self):
        # The data migration provides categories on every fresh database.
        self.assertTrue(Category.objects.filter(name="Информатика и программирование").exists())
        self.assertTrue(Category.objects.filter(name="Медицина и здравоохранение").exists())
        call_command("seed_student_examples", verbosity=0)
        self.assertEqual(Auction.objects.filter(title__startswith="[ДЕМО]").count(), 9)
        self.assertEqual(Auction.objects.filter(title__startswith="[ДЕМО]", status="open").count(), 6)
        self.assertGreaterEqual(Bid.objects.filter(auction__title__startswith="[ДЕМО]").count(), 12)
        demo_owner = User.objects.get(username="rea_demo_owner")
        self.assertFalse(demo_owner.has_usable_password())

        # Repeated Render deployments must not create duplicate sample orders.
        call_command("seed_student_examples", verbosity=0)
        self.assertEqual(Auction.objects.filter(title__startswith="[ДЕМО]").count(), 9)

    def test_published_examples_are_visible_in_regular_catalog(self):
        call_command("seed_student_examples", verbosity=0)
        user = User.objects.create_user(
            username="student_viewer", email="student_viewer@example.invalid",
            password="Student-Pass-Example-2026", email_verified=True,
        )
        self.client.force_login(user)
        response = self.client.get("/api/auctions/?status=open")
        self.assertEqual(response.status_code, 200)
        titles = [a["title"] for a in response.json()["results"]]
        self.assertTrue(any(title.startswith("[ДЕМО]") for title in titles))
