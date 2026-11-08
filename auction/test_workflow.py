"""Integration tests for winner delivery and owner review state machine."""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from auction.models import Auction, Bid, Category, TaskCompletion, User, WorkOrder, WorkSubmission
from auction.services import close_auction


class WorkFlowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(username="work_owner", email="work_owner@example.invalid",
            password="WorkOwner-test-2026!", email_verified=True)
        self.winner = User.objects.create_user(username="work_winner", email="work_winner@example.invalid",
            password="WorkWinner-test-2026!", email_verified=True)
        self.other = User.objects.create_user(username="work_other", email="work_other@example.invalid",
            password="WorkOther-test-2026!", email_verified=True)
        cat = Category.objects.create(name="Рабочие заказы")
        self.auction = Auction.objects.create(
            owner=self.owner, category=cat, title="Работа с данными",
            description="Выполнить подробный анализ наборов данных.",
            budget_kopecks=100000, ends_at=timezone.now() - timedelta(hours=1),
            due_at=timezone.now() + timedelta(days=2), status="open",
        )
        Bid.objects.create(auction=self.auction, bidder=self.winner, amount_kopecks=40000, idempotency_key="work-bid")
        close_auction(self.auction.pk)
        self.base = f"/api/auctions/{self.auction.pk}/work/"

    def auth(self, user):
        self.client.force_authenticate(user)

    def post(self, action, data=None, key=None):
        headers = {"HTTP_IDEMPOTENCY_KEY": key} if key else {}
        return self.client.post(self.base + action + "/", data or {}, format="json", **headers)

    def submit(self, key="work-submit", text="Разбор работы готов и доступен для проверки заказчиком."):
        return self.post("submit", {"result_text": text}, key=key)

    def test_complete_workflow_and_stats(self):
        self.auth(self.winner)
        self.assertEqual(self.client.get(self.base).data["status"], "not_started")
        self.assertEqual(self.post("start").status_code, 201)
        self.assertEqual(self.post("start").status_code, 200)
        self.assertEqual(self.submit().status_code, 201)
        self.assertEqual(self.client.get(self.base).data["status"], "submitted")
        self.assertEqual(self.client.get("/api/my/statistics/").data["completed_tasks_count"], 0)
        self.auth(self.owner)
        self.assertEqual(self.post("accept").status_code, 201)
        self.assertEqual(self.post("accept").status_code, 200)
        self.assertEqual(TaskCompletion.objects.filter(auction=self.auction).count(), 1)
        self.auth(self.winner)
        self.assertEqual(self.client.get("/api/my/statistics/").data["completed_tasks_count"], 1)
        view = self.client.get(self.base).data
        self.assertEqual(view["status"], "accepted")
        self.assertEqual(view["submissions"][0]["review_status"], "accepted")
        self.assertEqual(WorkSubmission.objects.count(), 1)

    def test_revision_with_history(self):
        self.auth(self.winner)
        self.post("start")
        self.submit("v1")
        self.auth(self.owner)
        revision = self.post("request-revision", {"feedback": "Добавьте таблицу с результатами."})
        self.assertEqual(revision.status_code, 200)
        self.assertEqual(revision.data["status"], "revision_requested")
        self.auth(self.winner)
        self.assertEqual(self.submit("v2", "Вторая версия готова: добавлена таблица с результатами проверки.").status_code, 201)
        self.assertEqual(self.client.get(self.base).data["submissions"][0]["feedback"], "Добавьте таблицу с результатами.")
        self.auth(self.owner)
        self.assertEqual(self.post("accept").status_code, 201)
        self.assertEqual(WorkSubmission.objects.count(), 2)
        self.assertEqual(list(WorkSubmission.objects.order_by("revision_number").values_list("review_status", flat=True)), ["revision", "accepted"])

    def test_permissions_and_hidden_history(self):
        self.auth(self.other)
        self.assertEqual(self.client.get(self.base).status_code, 404)
        for action in ("start", "submit", "accept", "request-revision"):
            self.assertIn(self.post(action, {"result_text": "Some sufficiently long result description.", "feedback": "Fix this"}, key="forbidden").status_code, (403, 404))
        self.auth(self.owner)
        self.assertEqual(self.post("start").status_code, 403)
        self.assertEqual(self.post("submit", {"result_text": "Owner cannot submit their work."}, key="owner").status_code, 403)
        self.auth(self.winner)
        self.assertEqual(self.post("accept").status_code, 403)
        self.assertEqual(self.post("request-revision", {"feedback": "Not ready"}).status_code, 403)
        self.auth(None)
        self.assertEqual(self.client.get(self.base).status_code, 403)

    def test_cannot_accept_before_delivery_and_no_bypass(self):
        self.auth(self.owner)
        self.assertEqual(self.post("accept").status_code, 409)
        self.assertEqual(self.client.post(f"/api/auctions/{self.auction.pk}/complete-work/", {}, format="json").status_code, 409)
        self.assertEqual(TaskCompletion.objects.count(), 0)

    def test_no_more_than_one_active_submission(self):
        self.auth(self.winner)
        self.post("start")
        self.assertEqual(self.submit("first").status_code, 201)
        self.assertEqual(self.submit("second", "Another report which is not currently allowed.").status_code, 409)
        self.assertEqual(WorkSubmission.objects.count(), 1)

    def test_idempotent_submit_and_conflicting_body(self):
        self.auth(self.winner)
        self.post("start")
        self.assertEqual(self.submit(key="key1").status_code, 201)
        self.assertEqual(self.submit(key="key1").status_code, 200)
        self.assertEqual(self.submit(key="key1", text="Different body but same key needs rejection.").status_code, 409)
        self.assertEqual(WorkSubmission.objects.count(), 1)

    def test_reject_invalid_payloads(self):
        self.auth(self.winner)
        self.post("start")
        self.assertEqual(self.post("submit", {"result_text": "Too short"}, key="bad").status_code, 400)
        self.assertEqual(self.post("submit", {"result_text": "This report is sufficiently long."}).status_code, 400)
        self.submit()
        self.auth(self.owner)
        self.assertEqual(self.post("request-revision", {"feedback": "no"}).status_code, 400)
        self.assertEqual(self.client.get(self.base).data["status"], "submitted")

    def test_other_user_banned_from_started_order(self):
        self.auth(self.winner)
        self.post("start")
        self.winner.is_active = False
        self.winner.save(update_fields=["is_active"])
        self.assertEqual(self.client.get(self.base).status_code, 403)
        self.assertEqual(self.submit().status_code, 403)

    def test_work_not_open_for_active_bidding(self):
        self.auction.status = "open"
        self.auction.save(update_fields=["status"])
        self.auth(self.winner)
        self.assertEqual(self.post("start").status_code, 409)
        self.assertEqual(self.client.get(self.base).status_code, 409)

    def test_notifications_on_delivery_and_revision(self):
        self.auth(self.winner)
        self.post("start")
        self.submit()
        self.auth(self.owner)
        notes = self.client.get("/api/notifications/").data["results"]
        self.assertTrue(any(n["type"] == "work_submitted" for n in notes))
        self.post("request-revision", {"feedback": "Исправьте пример расчёта."})
        self.auth(self.winner)
        notes = self.client.get("/api/notifications/").data["results"]
        self.assertTrue(any(n["type"] == "work_revision" for n in notes))
