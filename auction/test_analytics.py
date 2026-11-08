"""Tests for user KPIs, completed work, analytics security and exports."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from auction.models import Auction, Bid, Category, User, TaskCompletion
from auction.services import close_auction


class AnalyticsTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="analytics_owner", email="analytics_owner@example.invalid",
            password="Test-Pass-Analytics-2026!", email_verified=True,
        )
        self.winner = User.objects.create_user(
            username="analytics_winner", email="analytics_winner@example.invalid",
            password="Test-Pass-Analytics-2026!", email_verified=True,
        )
        self.loser = User.objects.create_user(
            username="analytics_loser", email="analytics_loser@example.invalid",
            password="Test-Pass-Analytics-2026!", email_verified=True,
        )
        self.admin = User.objects.create_superuser(
            username="analytics_admin", email="analytics_admin@example.invalid",
            password="Test-Pass-Analytics-2026!", email_verified=True,
        )
        cat = Category.objects.create(name="Аналитика")
        self.auction = Auction.objects.create(
            owner=self.owner, category=cat, title="Анализ задачи",
            description="Подробное описание задачи для проверки статистики.",
            budget_kopecks=100000,
            ends_at=timezone.now() - timedelta(days=1),
            due_at=timezone.now() + timedelta(days=4),
            status="open",
        )
        Bid.objects.create(
            auction=self.auction, bidder=self.winner,
            amount_kopecks=40000, idempotency_key="analytics-1",
        )
        Bid.objects.create(
            auction=self.auction, bidder=self.loser,
            amount_kopecks=60000, idempotency_key="analytics-2",
        )

    def auth(self, user):
        self.client.force_authenticate(user)

    def test_user_statistics_separate_bids_wins_completed(self):
        self.auth(self.winner)
        stats = self.client.get("/api/my/statistics/")
        self.assertEqual(stats.status_code, 200)
        self.assertEqual(stats.data["bids_count"], 1)
        self.assertEqual(stats.data["wins_count"], 0)
        self.assertEqual(stats.data["completed_tasks_count"], 0)
        close_auction(self.auction.pk)
        stats = self.client.get("/api/my/statistics/").data
        self.assertEqual(stats["wins_count"], 1)
        self.assertEqual(stats["completed_tasks_count"], 0)
        self.assertEqual(stats["win_rate_percent"], 100)
        self.auth(self.loser)
        loser = self.client.get("/api/my/statistics/").data
        self.assertEqual(loser["bids_count"], 1)
        self.assertEqual(loser["wins_count"], 0)

    def test_only_owner_can_confirm_genuine_delivery(self):
        self.auth(self.owner)
        url = f"/api/auctions/{self.auction.pk}/complete-work/"
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 409)
        close_auction(self.auction.pk)

        self.auth(self.winner)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 403)

        self.auth(self.winner)
        self.assertEqual(self.client.post(f"/api/auctions/{self.auction.pk}/work/start/", {}, format="json").status_code, 201)
        self.assertEqual(self.client.post(f"/api/auctions/{self.auction.pk}/work/submit/", {
            "result_text": "Полный подробный результат доступен для проверки заказчиком."
        }, format="json", HTTP_IDEMPOTENCY_KEY="analytics-v1").status_code, 201)
        self.auth(self.owner)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 201)
        self.assertEqual(self.client.post(url, {}, format="json").status_code, 200)
        self.assertEqual(TaskCompletion.objects.filter(auction=self.auction).count(), 1)

        self.auth(self.winner)
        self.assertEqual(self.client.get("/api/my/statistics/").data["completed_tasks_count"], 1)
        completion = self.client.get(f"/api/auctions/{self.auction.pk}/completion/")
        self.assertTrue(completion.data["completed"])

    def test_regular_user_cannot_get_admin_analytics_or_csv(self):
        self.auth(self.winner)
        for url in [
            "/api/admin/analytics/",
            "/api/admin/reports/?kind=users",
            "/api/admin/reports/?kind=bids",
            "/api/admin/reports/?kind=auctions",
        ]:
            self.assertEqual(self.client.get(url).status_code, 403, url)
        self.auth(None)
        self.assertEqual(self.client.get("/api/my/statistics/").status_code, 403)

    def test_admin_dashboard_and_export_use_actual_data(self):
        close_auction(self.auction.pk)
        self.auth(self.admin)
        response = self.client.get("/api/admin/analytics/")
        self.assertEqual(response.status_code, 200, response.data)
        summary = response.data["summary"]
        self.assertEqual(summary["users_total"], 4)
        self.assertEqual(summary["auctions_total"], 1)
        self.assertEqual(summary["bids_total"], 2)
        self.assertEqual(summary["auctions_closed"], 1)
        self.assertEqual(summary["completed_tasks"], 0)
        self.assertEqual(summary["payment_total_kopecks"], 60000)
        self.assertEqual(response.data["by_category"][0]["count"], 1)
        self.assertEqual(response.data["by_month"][0]["closed_count"], 1)
        for kind in ("users", "auctions", "bids"):
            export = self.client.get(f"/api/admin/reports/?kind={kind}")
            self.assertEqual(export.status_code, 200)
            self.assertIn("text/csv", export["Content-Type"])
            self.assertIn("rea_" + kind, export["Content-Disposition"])
        self.assertEqual(self.client.get("/api/admin/reports/?kind=unknown").status_code, 400)

    def test_no_false_completions_in_admin_analytics(self):
        close_auction(self.auction.pk)
        self.auth(self.admin)
        self.assertEqual(self.client.get("/api/admin/analytics/").data["summary"]["completed_tasks"], 0)
        self.auth(self.winner)
        self.client.post(f"/api/auctions/{self.auction.pk}/work/start/", {}, format="json")
        self.client.post(f"/api/auctions/{self.auction.pk}/work/submit/", {
            "result_text": "Новая работа завершена и передана заказчику на проверку."
        }, format="json", HTTP_IDEMPOTENCY_KEY="analytics-v2")
        self.auth(self.owner)
        self.client.post(f"/api/auctions/{self.auction.pk}/complete-work/", {}, format="json")
        self.auth(self.admin)
        self.assertEqual(self.client.get("/api/admin/analytics/").data["summary"]["completed_tasks"], 1)

    def test_export_neutralizes_spreadsheet_formula_input(self):
        self.auction.title = "=INJECTION()"
        self.auction.save(update_fields=["title"])
        self.auth(self.admin)
        export = self.client.get("/api/admin/reports/?kind=auctions")
        text = export.content.decode("utf-8-sig")
        self.assertIn("'=INJECTION()", text)
