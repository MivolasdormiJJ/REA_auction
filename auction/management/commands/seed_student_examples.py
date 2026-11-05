"""Public educational auction examples. Safe to rerun; no login credentials are created."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from auction.models import Auction, Bid, Category, User
from auction.services import close_auction


SAMPLES = [
    ("[ДЕМО] Разработать учебный веб-сайт", "Информатика и программирование",
     "Создать адаптивный сайт для студенческого проекта: главная страница, формы и понятная навигация.", 4500000, "open", 21),
    ("[ДЕМО] Проанализировать открытый датасет", "Искусственный интеллект и анализ данных",
     "Провести исследовательский анализ общедоступных данных, построить графики и оформить выводы.", 3000000, "open", 19),
    ("[ДЕМО] Разработать логотип клуба", "Дизайн и цифровое искусство",
     "Подготовить три визуальные концепции логотипа студенческого клуба и исходники в SVG.", 1800000, "open", 23),
    ("[ДЕМО] Перевести аннотацию исследования", "Лингвистика и перевод",
     "Перевести научную аннотацию с английского на русский язык с сохранением терминологии.", 1200000, "open", 25),
    ("[ДЕМО] Подготовить маркетинговый план", "Маркетинг и реклама",
     "Предложить план продвижения студенческого события, сегменты аудитории и пример бюджета.", 2600000, "open", 28),
    ("[ДЕМО] Математическая визуализация", "Математика и прикладная математика",
     "Подготовить интерактивную визуализацию функций для открытого учебного занятия.", 2000000, "open", 30),
    ("[ДЕМО] Макет афиши мероприятия", "Дизайн и цифровое искусство",
     "Подготовить постер события с печатным макетом и версией для социальных сетей.", 900000, "closed", -2),
    ("[ДЕМО] Психологический опрос", "Психология",
     "Подготовить анонимный опрос для учебного исследования с ясными вопросами и методикой.", 1600000, "review", 20),
    ("[ДЕМО] Справочник терминов", "Филология и журналистика",
     "Составить понятный справочник профильных терминов для учебного курса.", 1100000, "draft", 26),
]


class Command(BaseCommand):
    help = "Populate public demonstration auctions and categories without demo passwords"

    @transaction.atomic
    def handle(self, *args, **options):
        # ПРОБЛЕМА: тестовый контент не должен выдавать аккаунты с общими паролями.
        # РЕШЕНИЕ: технические владельцы/участники не могут войти по паролю.
        users = {}
        for username in ["rea_demo_owner", "rea_demo_alex", "rea_demo_maria", "rea_demo_ivan"]:
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": username + "@example.invalid", "email_verified": True},
            )
            if created:
                user.set_unusable_password()
                user.save(update_fields=["password"])
            users[username] = user

        now = timezone.now()
        created_count = 0
        for idx, (title, category_name, description, budget, state, offset) in enumerate(SAMPLES):
            category, _ = Category.objects.get_or_create(name=category_name)
            if Auction.objects.filter(owner=users["rea_demo_owner"], title=title).exists():
                continue
            ends_at = now + timedelta(days=offset)
            auction = Auction.objects.create(
                owner=users["rea_demo_owner"], category=category, title=title,
                description=description, budget_kopecks=budget,
                ends_at=ends_at,
                due_at=now + timedelta(days=max(offset + 7, 2)),
                status="open" if state == "closed" else state,
            )
            created_count += 1
            if state in ["open", "closed"]:
                # Отдельные демо-предложения, никогда не от имени реальных пользователей.
                for j, name in enumerate(["rea_demo_alex", "rea_demo_maria", "rea_demo_ivan"][:2 + idx % 2]):
                    Bid.objects.create(
                        auction=auction, bidder=users[name],
                        amount_kopecks=budget - (j + 1) * budget // 10,
                        idempotency_key=f"public-sample-{idx}-{j}",
                    )
            if state == "closed":
                close_auction(auction.id)

        self.stdout.write(f"Student demo catalog ready; new auctions: {created_count}")
