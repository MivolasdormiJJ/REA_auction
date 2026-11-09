from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from auction.models import Auction, Category, ChatMessage, Event, User


class ChatTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.owner = User.objects.create_user(
            username="chat_owner", email="chat_owner@example.invalid",
            password="Chat-owner-test-2026!", email_verified=True,
        )
        self.winner = User.objects.create_user(
            username="chat_winner", email="chat_winner@example.invalid",
            password="Chat-winner-test-2026!", email_verified=True,
        )
        self.other = User.objects.create_user(
            username="chat_other", email="chat_other@example.invalid",
            password="Chat-other-test-2026!", email_verified=True,
        )
        self.admin = User.objects.create_superuser(
            username="chat_admin", email="chat_admin@example.invalid",
            password="Chat-admin-test-2026!", email_verified=True,
        )
        category = Category.objects.create(name="Chat tests")
        self.auction = Auction.objects.create(
            owner=self.owner, category=category, title="Private chat order",
            description="A sufficiently detailed closed auction for private chat tests.",
            budget_kopecks=100000, ends_at=timezone.now() - timedelta(days=2),
            due_at=timezone.now() + timedelta(days=2), status=Auction.Status.CLOSED,
            winner=self.winner, payment_kopecks=80000, closed_at=timezone.now() - timedelta(days=1),
        )
        self.url = f"/api/auctions/{self.auction.pk}/chat/"

    def auth(self, user):
        self.client.force_authenticate(user)

    def send(self, body="Здравствуйте! Когда будет готов итоговый результат?", key="chat-key"):
        return self.client.post(
            self.url, {"body": body}, format="json", HTTP_IDEMPOTENCY_KEY=key,
        )

    def test_participants_exchange_and_poll_messages(self):
        self.auth(self.owner)
        first = self.send()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["sender_username"], self.owner.username)

        self.auth(self.winner)
        second = self.send("Здравствуйте! Работа будет готова сегодня к вечеру.", "winner-key")
        self.assertEqual(second.status_code, 201)
        history = self.client.get(self.url)
        self.assertEqual([item["id"] for item in history.data["results"]], [first.data["id"], second.data["id"]])
        self.assertEqual(history.data["owner"]["username"], self.owner.username)
        self.assertEqual(history.data["winner"]["username"], self.winner.username)
        poll = self.client.get(self.url, {"after": first.data["id"]})
        self.assertEqual([item["id"] for item in poll.data["results"]], [second.data["id"]])
        self.assertEqual(Event.objects.filter(action="chat_message_sent").count(), 2)

    def test_chat_is_private_and_admin_is_read_only(self):
        self.auth(self.owner)
        self.send()
        self.auth(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 404)
        self.assertEqual(self.send(key="other-key").status_code, 404)
        self.auth(self.admin)
        self.assertEqual(self.client.get(self.url).status_code, 200)
        self.assertEqual(self.send(key="admin-key").status_code, 404)
        self.auth(None)
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_chat_opens_only_after_auction_has_winner(self):
        self.auction.status = Auction.Status.OPEN
        self.auction.save(update_fields=["status"])
        self.auth(self.owner)
        self.assertEqual(self.client.get(self.url).status_code, 409)
        self.assertEqual(self.send().status_code, 409)
        self.auction.status = Auction.Status.CLOSED
        self.auction.winner = None
        self.auction.save(update_fields=["status", "winner"])
        self.assertEqual(self.client.get(self.url).status_code, 409)

    def test_idempotency_and_payload_validation(self):
        self.auth(self.owner)
        first = self.send()
        replay = self.send()
        self.assertEqual((first.status_code, replay.status_code), (201, 200))
        self.assertEqual(first.data["id"], replay.data["id"])
        self.assertEqual(ChatMessage.objects.count(), 1)
        self.assertEqual(self.send("Другое сообщение с тем же ключом").status_code, 409)
        self.assertEqual(self.send("   ", "blank-key").status_code, 400)
        self.assertEqual(self.send("x" * 2001, "long-key").status_code, 400)
        self.assertEqual(self.client.post(self.url, {"body": "Нет ключа"}, format="json").status_code, 400)
        self.assertEqual(self.client.get(self.url, {"after": "wrong"}).status_code, 400)

    def test_incoming_message_appears_in_notifications_only_for_recipient(self):
        self.auth(self.owner)
        sent = self.send("Пожалуйста, пришлите итоговый файл и краткую инструкцию.")
        self.assertEqual(sent.status_code, 201)
        owner_notices = self.client.get("/api/notifications/").data["results"]
        self.assertFalse(any(item["id"] == f"chat-message-{sent.data['id']}" for item in owner_notices))
        self.auth(self.winner)
        winner_notices = self.client.get("/api/notifications/").data["results"]
        self.assertTrue(any(item["id"] == f"chat-message-{sent.data['id']}" for item in winner_notices))
