"""Outcome notifications are scoped to the account and never announce premature winners."""
from datetime import timedelta
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient
from auction.models import Auction, Bid, Category, User
from auction.services import close_auction


class NotificationTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="notice_owner", email="notice_owner@example.invalid", password="SomePassword-2026!", email_verified=True)
        self.winner = User.objects.create_user(username="notice_winner", email="notice_winner@example.invalid", password="SomePassword-2026!", email_verified=True)
        self.loser = User.objects.create_user(username="notice_loser", email="notice_loser@example.invalid", password="SomePassword-2026!", email_verified=True)
        self.stranger = User.objects.create_user(username="notice_stranger", email="notice_stranger@example.invalid", password="SomePassword-2026!", email_verified=True)
        cat = Category.objects.create(name="Results testing")
        self.a = Auction.objects.create(
            owner=self.owner, category=cat, title="Задача для результатов",
            description="Демонстрационный аукцион для проверки уведомлений о результатах.",
            budget_kopecks=100000, ends_at=timezone.now()+timedelta(days=1),
            due_at=timezone.now()+timedelta(days=2), status="open",
        )
        Bid.objects.create(auction=self.a, bidder=self.winner, amount_kopecks=40000, idempotency_key="a")
        Bid.objects.create(auction=self.a, bidder=self.loser, amount_kopecks=60000, idempotency_key="b")

    def notices_for(self, user):
        self.client.force_authenticate(user)
        return self.client.get("/api/notifications/")

    def test_no_results_before_auction_closes(self):
        for u in (self.owner, self.winner, self.loser, self.stranger):
            response = self.notices_for(u)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["results"], [])

    def test_winner_loser_owner_receive_correct_results(self):
        Auction.objects.filter(pk=self.a.pk).update(ends_at=timezone.now()-timedelta(seconds=1))
        close_auction(self.a.pk)
        winning = self.notices_for(self.winner).data["results"]
        losing = self.notices_for(self.loser).data["results"]
        owner = self.notices_for(self.owner).data["results"]
        self.assertEqual(len(winning), 1)
        self.assertEqual(winning[0]["type"], "auction_won")
        self.assertEqual(winning[0]["payment_kopecks"], 60000)
        self.assertEqual(losing[0]["type"], "auction_lost")
        self.assertIsNone(losing[0]["payment_kopecks"])
        self.assertEqual(owner[0]["type"], "auction_owner_closed")
        self.assertEqual(self.notices_for(self.stranger).data["count"], 0)

    def test_anonymous_cannot_view_results(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/notifications/").status_code, 403)
