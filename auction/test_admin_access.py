"""Access controls for administrative data and visible auction offers."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from auction.models import Auction, Bid, Category, User


class ManagementAccessTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.admin = User.objects.create_superuser(
            username="test_admin", email="administrator@test.invalid", password="VeryStrongAdminPwd123!",
            email_verified=True,
        )
        self.owner = User.objects.create_user(
            username="test_owner", email="owner@test.invalid", password="VeryStrongOwnerPwd123!",
            email_verified=True,
        )
        self.bidder = User.objects.create_user(
            username="test_bidder", email="bidder@test.invalid", password="VeryStrongBidderPwd123!",
            email_verified=True,
        )
        cat = Category.objects.create(name="Тестовая категория")
        self.draft = Auction.objects.create(
            owner=self.owner, category=cat, title="Частный черновик",
            description="Пример не опубликованной задачи, скрытой от чужих пользователей.",
            budget_kopecks=100000,
            ends_at=timezone.now() + timedelta(days=4),
            due_at=timezone.now() + timedelta(days=7),
            status="draft",
        )
        self.open = Auction.objects.create(
            owner=self.owner, category=cat, title="Публичный аукцион",
            description="Пример опубликованной задачи с открытыми предложениями.",
            budget_kopecks=100000,
            ends_at=timezone.now() + timedelta(days=4),
            due_at=timezone.now() + timedelta(days=7),
            status="open",
        )
        Bid.objects.create(
            auction=self.open, bidder=self.bidder, amount_kopecks=70000,
            idempotency_key="test-visible",
        )

    def test_superuser_can_view_all_users_and_private_auctions(self):
        self.client.force_authenticate(self.admin)
        users = self.client.get("/api/admin/users/")
        self.assertEqual(users.status_code, 200)
        self.assertGreaterEqual(users.data["count"], 3)
        for row in users.data["results"]:
            self.assertNotIn("password", row)
        auctions = self.client.get("/api/admin/auctions/")
        self.assertEqual(auctions.status_code, 200)
        ids = {a["id"] for a in auctions.data["results"]}
        self.assertIn(self.draft.id, ids)
        self.assertEqual(self.client.get(f"/api/auctions/{self.draft.id}/").status_code, 200)

    def test_admin_data_hidden_from_regular_and_anonymous_users(self):
        for account in [self.owner, self.bidder, None]:
            self.client.force_authenticate(account)
            self.assertEqual(self.client.get("/api/admin/users/").status_code, 403)
            self.assertEqual(self.client.get("/api/admin/auctions/").status_code, 403)
        self.client.force_authenticate(self.bidder)
        self.assertEqual(self.client.get(f"/api/auctions/{self.draft.id}/").status_code, 404)

    def test_bids_are_public_to_signed_in_users_but_not_anon(self):
        for user in [self.admin, self.owner, self.bidder]:
            self.client.force_authenticate(user)
            result = self.client.get(f"/api/auctions/{self.open.id}/bids/")
            self.assertEqual(result.status_code, 200)
            self.assertEqual(result.data[0]["bidder_username"], "test_bidder")
            self.assertEqual(result.data[0]["amount_kopecks"], 70000)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(f"/api/auctions/{self.open.id}/bids/").status_code, 403)

    def test_owner_cannot_bid_even_with_admin_role(self):
        self.client.force_authenticate(self.owner)
        response = self.client.post(
            f"/api/auctions/{self.open.id}/bids/",
            {"amount_kopecks": 50000},
            format="json", HTTP_IDEMPOTENCY_KEY="test-owner",
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.open.bids.count(), 1)
