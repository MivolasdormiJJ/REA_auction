from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from auction.models import Auction, Category, Review, TaskCompletion, User


class ReviewTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="review_test_owner", email="review_test_owner@example.invalid",
            password="Review-test-owner-2026!", email_verified=True,
        )
        self.performer = User.objects.create_user(
            username="review_test_performer", email="review_test_performer@example.invalid",
            password="Review-test-performer-2026!", email_verified=True,
        )
        self.other = User.objects.create_user(
            username="review_test_other", email="review_test_other@example.invalid",
            password="Review-test-other-2026!", email_verified=True,
        )
        category = Category.objects.create(name="Review tests")
        self.auction = Auction.objects.create(
            owner=self.owner, category=category, title="Accepted reviewed job",
            description="A sufficiently detailed accepted job for review tests.",
            budget_kopecks=100000, ends_at=timezone.now() - timedelta(days=3),
            due_at=timezone.now() - timedelta(days=1), status=Auction.Status.CLOSED,
            winner=self.performer, payment_kopecks=80000, closed_at=timezone.now() - timedelta(days=2),
        )
        TaskCompletion.objects.create(auction=self.auction, confirmed_by=self.owner)
        self.url = f"/api/auctions/{self.auction.pk}/review/"

    def test_owner_creates_review_and_reputation_updates(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(self.url, {
            "rating": 5,
            "comment": "Работа выполнена отлично и полностью соответствует техническому заданию.",
        }, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Review.objects.get().performer, self.performer)
        self.assertNotIn("email", response.data)

        profile = self.client.get(f"/api/performers/{self.performer.pk}/reputation/")
        self.assertEqual(profile.status_code, 200)
        self.assertEqual(profile.data["average_rating"], 5.0)
        self.assertEqual(profile.data["reviews_count"], 1)
        self.assertNotIn("email", profile.data["performer"])
        stats = self.client.get("/api/my/statistics/")
        self.assertEqual(stats.data["reviews_count"], 0)

    def test_review_is_single_and_owner_only(self):
        payload = {"rating": 4, "comment": "Хороший результат, все основные требования были выполнены вовремя."}
        self.client.force_authenticate(self.other)
        self.assertEqual(self.client.post(self.url, payload, format="json").status_code, 403)
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.post(self.url, payload, format="json").status_code, 201)
        self.assertEqual(self.client.post(self.url, payload, format="json").status_code, 409)
        self.assertEqual(Review.objects.count(), 1)

    def test_rejects_unaccepted_and_invalid_reviews(self):
        TaskCompletion.objects.all().delete()
        self.client.force_authenticate(self.owner)
        valid = {"rating": 5, "comment": "Достаточно длинный комментарий о выполненной работе."}
        self.assertEqual(self.client.post(self.url, valid, format="json").status_code, 409)
        TaskCompletion.objects.create(auction=self.auction, confirmed_by=self.owner)
        for payload in [
            {"rating": 0, "comment": valid["comment"]},
            {"rating": 6, "comment": valid["comment"]},
            {"rating": 5, "comment": "коротко"},
        ]:
            self.assertEqual(self.client.post(self.url, payload, format="json").status_code, 400)
        self.assertEqual(Review.objects.count(), 0)
