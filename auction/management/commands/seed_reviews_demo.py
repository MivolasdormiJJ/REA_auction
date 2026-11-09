"""Local visual demo for performer reviews and ratings."""
from datetime import timedelta

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from auction.models import (
    Auction, Bid, Category, ChatMessage, Review, TaskCompletion, User, WorkOrder, WorkSubmission,
)


PASSWORD = "Reviews-demo-2026!"


class Command(BaseCommand):
    help = "Only in DEBUG: create review/rating demo accounts and accepted orders"

    @transaction.atomic
    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError("Review demo accounts are forbidden when DEBUG=0")

        users = {}
        for username in ["review_owner", "review_performer", "review_client_anna", "review_client_oleg", "review_newcomer"]:
            user, _ = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.invalid", "email_verified": True},
            )
            user.email_verified = True
            user.is_active = True
            user.set_password(PASSWORD)
            user.save(update_fields=["password", "email_verified", "is_active"])
            users[username] = user

        category, _ = Category.objects.get_or_create(name="Демонстрация отзывов")
        now = timezone.now()

        def accepted_order(owner, title, days_ago, rating=None, comment=""):
            auction, created = Auction.objects.get_or_create(
                owner=owner,
                title=title,
                defaults={
                    "category": category,
                    "description": "Демонстрационный завершённый заказ для показа отзывов и рейтинга исполнителя.",
                    "budget_kopecks": 1500000,
                    "ends_at": now - timedelta(days=days_ago + 4),
                    "due_at": now - timedelta(days=days_ago),
                    "status": Auction.Status.CLOSED,
                    "winner": users["review_performer"],
                    "payment_kopecks": 1200000,
                    "closed_at": now - timedelta(days=days_ago + 3),
                },
            )
            if created:
                Bid.objects.create(
                    auction=auction, bidder=users["review_performer"],
                    amount_kopecks=1100000, idempotency_key=f"review-demo-{auction.pk}-winner",
                )
                Bid.objects.create(
                    auction=auction, bidder=users["review_newcomer"],
                    amount_kopecks=1200000, idempotency_key=f"review-demo-{auction.pk}-second",
                )
            order, _ = WorkOrder.objects.get_or_create(
                auction=auction,
                defaults={"status": WorkOrder.Status.ACCEPTED, "accepted_at": now - timedelta(days=days_ago)},
            )
            if order.status != WorkOrder.Status.ACCEPTED:
                order.status = WorkOrder.Status.ACCEPTED
                order.accepted_at = now - timedelta(days=days_ago)
                order.save(update_fields=["status", "accepted_at", "updated_at"])
            submission, _ = WorkSubmission.objects.get_or_create(
                order=order, revision_number=1,
                defaults={
                    "idempotency_key": f"review-demo-submission-{auction.pk}",
                    "result_text": "Работа выполнена в полном объёме. Результаты, исходные материалы и инструкция переданы заказчику.",
                    "review_status": WorkSubmission.Review.ACCEPTED,
                    "reviewed_at": now - timedelta(days=days_ago),
                },
            )
            if submission.review_status != WorkSubmission.Review.ACCEPTED:
                submission.review_status = WorkSubmission.Review.ACCEPTED
                submission.reviewed_at = now - timedelta(days=days_ago)
                submission.save(update_fields=["review_status", "reviewed_at"])
            TaskCompletion.objects.get_or_create(auction=auction, defaults={"confirmed_by": owner})
            if rating is not None:
                Review.objects.get_or_create(
                    auction=auction,
                    defaults={
                        "reviewer": owner,
                        "performer": users["review_performer"],
                        "rating": rating,
                        "comment": comment,
                    },
                )
            return auction

        pending = accepted_order(
            users["review_owner"],
            "[ОТЗЫВЫ] Лендинг студенческой конференции — оставьте отзыв",
            1,
        )
        accepted_order(
            users["review_client_anna"],
            "[ОТЗЫВЫ] Аналитический дашборд",
            12,
            5,
            "Отличная работа: дашборд получился понятным, быстрым и полностью соответствует техническому заданию. Исполнитель всегда был на связи.",
        )
        accepted_order(
            users["review_client_oleg"],
            "[ОТЗЫВЫ] Автоматизация отчёта",
            25,
            4,
            "Результат качественный и сдан вовремя. Потребовалось небольшое уточнение по форматированию, которое исполнитель быстро внёс.",
        )
        accepted_order(
            users["review_owner"],
            "[ОТЗЫВЫ] Прототип мобильного интерфейса",
            40,
            5,
            "Исполнитель предложил несколько сильных вариантов и подробно объяснил решения. Итоговый прототип отлично подошёл для презентации.",
        )

        pending.refresh_from_db()
        demo_messages = [
            (users["review_owner"], "Здравствуйте! Уточните, пожалуйста, когда сможете передать финальные исходники?"),
            (users["review_performer"], "Здравствуйте! Финальную версию и инструкцию подготовлю сегодня до 18:00."),
            (users["review_owner"], "Отлично, спасибо. Добавьте, пожалуйста, также мобильный вариант страницы."),
        ]
        for index, (sender, body) in enumerate(demo_messages, start=1):
            ChatMessage.objects.get_or_create(
                auction=pending,
                sender=sender,
                idempotency_key=f"chat-demo-{index}",
                defaults={"body": body},
            )
        self.stdout.write(self.style.SUCCESS(
            "Review and chat demo ready. Password for all accounts: " + PASSWORD
        ))
        self.stdout.write(
            f"Customer: review_owner; performer: review_performer; reviewable auction id: {pending.pk}"
        )
