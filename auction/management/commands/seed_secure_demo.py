"""Create isolated demonstration accounts and auctions from encrypted credentials.

Requires DEMO_SEED_ENABLED=1, DEMO_CREDENTIALS_ENC, DEMO_SEED_KEY.
Secrets are NEVER committed; use Render secret environment variables.
"""
import json
import os
from datetime import timedelta

from cryptography.fernet import Fernet, InvalidToken
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from auction.models import Auction, Bid, Category, User
from auction.services import close_auction


class Command(BaseCommand):
    help = "Seed demonstration-only accounts, offers and auction examples"

    def handle(self, *args, **options):
        if os.environ.get("DEMO_SEED_ENABLED") != "1":
            return
        ciphertext = os.environ.get("DEMO_CREDENTIALS_ENC", "")
        key = os.environ.get("DEMO_SEED_KEY", "")
        if not ciphertext or not key:
            raise CommandError("Demo seed is enabled but the encrypted credentials or key are missing")
        try:
            data = json.loads(Fernet(key.encode()).decrypt(ciphertext.encode()))
        except (InvalidToken, ValueError, TypeError) as exc:
            raise CommandError("Cannot decrypt demonstration credentials") from exc

        expected = {"demo_admin", "demo_owner", "demo_alex", "demo_maria", "demo_ivan"}
        if {record["username"] for record in data["users"]} != expected:
            raise CommandError("Unexpected test credentials manifest")

        with transaction.atomic():
            users = {}
            for entry in data["users"]:
                username = entry["username"]
                role = entry["role"]
                existing = User.objects.filter(username=username).first()
                if existing:
                    # NEVER reset an existing user's credentials or escalate permissions.
                    if existing.email != entry["email"]:
                        raise CommandError("Conflicting pre-existing demo username")
                    users[username] = existing
                    continue
                if User.objects.filter(email=entry["email"]).exists():
                    raise CommandError("Conflicting pre-existing demo email")
                person = User.objects.create_user(
                    username=username, email=entry["email"], password=entry["password"],
                    email_verified=True, is_active=True,
                    is_staff=role == "admin", is_superuser=role == "admin",
                )
                users[username] = person

            owner = users["demo_owner"]
            category_map = {}
            for label in ["Разработка", "Дизайн", "Маркетинг", "Перевод"]:
                category_map[label], _ = Category.objects.get_or_create(name=label)
            now = timezone.now()
            fixtures = [
                ("[ДЕМО] Разработать лендинг", "Разработка", "Создать адаптивную посадочную страницу на React по техническому заданию. Макет и тексты предоставляются.", 8500000, "open", 8),
                ("[ДЕМО] Дизайн логотипа", "Дизайн", "Нарисовать три оригинальные концепции логотипа и передать итог в SVG, PDF и PNG с описанием цветов.", 3500000, "open", 5),
                ("[ДЕМО] Интеграция с CRM", "Разработка", "Подключить CRM по API, синхронизировать заявки и настроить журнал ошибок с документацией.", 12000000, "open", 12),
                ("[ДЕМО] Перевести документацию", "Перевод", "Перевести англоязычное руководство на русский язык, сохранить ссылки и форматирование.", 2400000, "closed", -1),
                ("[ДЕМО] Создать фирменный стиль", "Дизайн", "Разработать фирменные цвета, типографику, шаблоны презентации и руководство по бренду.", 7000000, "draft", 14),
                ("[ДЕМО] Маркетинговое исследование", "Маркетинг", "Подготовить обзор аудитории и конкурентов, оформить рекомендации и презентацию.", 6000000, "review", 9),
            ]
            for i, (title, category, description, budget, state, offset) in enumerate(fixtures):
                a, created = Auction.objects.get_or_create(
                    owner=owner, title=title,
                    defaults={
                        "category": category_map[category], "description": description,
                        "budget_kopecks": budget,
                        "ends_at": now + timedelta(days=offset),
                        "due_at": now + timedelta(days=max(offset + 7, 2)),
                        "status": "open" if state == "closed" else state,
                    },
                )
                if not created:
                    continue
                if state in ("open", "closed"):
                    names = ["demo_alex", "demo_maria", "demo_ivan"]
                    for j, name in enumerate(names[:3 if i % 2 == 0 else 2]):
                        Bid.objects.create(
                            auction=a, bidder=users[name],
                            amount_kopecks=budget - (j + 1) * (budget // 10),
                            idempotency_key=f"demo-fixture-{i}-{j}",
                        )
                if state == "closed":
                    close_auction(a.pk)

        self.stdout.write("Demo users and example auctions are ready (no passwords printed)")
