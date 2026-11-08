"""Private work portfolio tests, including paging and acceptance changes."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from auction.models import Auction, Bid, Category, TaskCompletion, User, WorkOrder, WorkSubmission


class MyWorksTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="portfolio_owner", email="portfolio_owner@example.invalid",
            email_verified=True, password="Portfolio-test-password-2026!")
        self.winner = User.objects.create_user(username="portfolio_winner", email="portfolio_winner@example.invalid",
            email_verified=True, password="Portfolio-test-password-2026!")
        self.other = User.objects.create_user(username="portfolio_other", email="portfolio_other@example.invalid",
            email_verified=True, password="Portfolio-test-password-2026!")
        self.category = Category.objects.create(name="Портфолио")
        self.active = self.auction("Выполняется", winner=self.winner)
        self.accepted = self.auction("Принята", winner=self.winner)
        self.foreign = self.auction("Чужая", winner=self.other)
        self.open = self.auction("Ещё торги", winner=self.winner, status="open")
        active_order = WorkOrder.objects.create(auction=self.active, status=WorkOrder.Status.SUBMITTED)
        WorkSubmission.objects.create(order=active_order, revision_number=1,
            idempotency_key="portfolio-deliver-1", result_text="Подробный готовый результат работы для приёмки")
        accepted_order = WorkOrder.objects.create(auction=self.accepted, status=WorkOrder.Status.ACCEPTED)
        WorkSubmission.objects.create(order=accepted_order, revision_number=1,
            idempotency_key="portfolio-deliver-2", result_text="Принятая работа с подробным итоговым результатом",
            review_status=WorkSubmission.Review.ACCEPTED)
        TaskCompletion.objects.create(auction=self.accepted, confirmed_by=self.owner)

    def auction(self, title, winner, status="closed"):
        now = timezone.now()
        return Auction.objects.create(owner=self.owner, winner=winner, category=self.category,
            title=title, description="Достаточно подробное описание задания для тестов",
            budget_kopecks=200000, payment_kopecks=150000 if status == "closed" else None,
            ends_at=now - timedelta(days=2) if status == "closed" else now + timedelta(days=2),
            due_at=now + timedelta(days=5), status=status,
            closed_at=now - timedelta(days=1) if status == "closed" else None)

    def test_only_winner_can_see_own_works(self):
        self.client.force_authenticate(self.winner)
        active = self.client.get("/api/my/works/?status=active")
        self.assertEqual(active.status_code, 200)
        self.assertEqual(active.data["count"], 1)
        self.assertEqual(active.data["results"][0]["auction_id"], self.active.id)
        self.assertEqual(active.data["results"][0]["status"], "submitted")
        self.assertEqual(active.data["results"][0]["latest_revision"], 1)
        self.assertIn("Подробный", active.data["results"][0]["latest_result"])
        accepted = self.client.get("/api/my/works/?status=accepted")
        self.assertEqual(accepted.data["count"], 1)
        self.assertEqual(accepted.data["results"][0]["status"], "accepted")
        self.assertNotIn(self.foreign.id, [w["auction_id"] for w in accepted.data["results"]])
        self.assertNotIn(self.open.id, [w["auction_id"] for w in active.data["results"]])

    def test_owner_does_not_get_bidders_private_portfolio(self):
        self.client.force_authenticate(self.owner)
        self.assertEqual(self.client.get("/api/my/works/").data["count"], 0)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/my/works/").status_code, 403)

    def test_invalid_filters_and_pagination(self):
        self.client.force_authenticate(self.winner)
        self.assertEqual(self.client.get("/api/my/works/?status=invalid").status_code, 400)
        self.assertEqual(self.client.get("/api/my/works/?page=not-a-number").status_code, 404)

    def test_completion_moves_work_to_accepted(self):
        self.client.force_authenticate(self.winner)
        self.assertEqual(self.client.get("/api/my/works/?status=active").data["count"], 1)
        TaskCompletion.objects.create(auction=self.active, confirmed_by=self.owner)
        self.assertEqual(self.client.get("/api/my/works/?status=active").data["count"], 0)
        self.assertEqual(self.client.get("/api/my/works/?status=accepted").data["count"], 2)
