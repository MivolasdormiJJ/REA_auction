"""Создать один первый production-аккаунт из секретных переменных Render.

После создания переменные BOOTSTRAP_USERNAME и BOOTSTRAP_PASSWORD необходимо удалить.
Команда намеренно НЕ изменяет пароль существующего пользователя и НЕ выдаёт права модератора.
"""
import os

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as PasswordValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from auction.models import User


class Command(BaseCommand):
    help = "Однократно создать подтверждённого пользователя из BOOTSTRAP_*"

    def handle(self, *args, **options):
        username = os.environ.get("BOOTSTRAP_USERNAME", "").strip()
        password = os.environ.get("BOOTSTRAP_PASSWORD", "")
        if not username and not password:
            # ПРОБЛЕМА: запуск приложения не должен зависеть от bootstrap-секретов.
            # РЕШЕНИЕ: без обеих переменных команда безопасно ничего не делает.
            return
        if not username or not password:
            raise CommandError("Обе переменные BOOTSTRAP_USERNAME и BOOTSTRAP_PASSWORD обязательны")
        if len(password) < 12:
            raise CommandError("Пароль первого аккаунта должен содержать не менее 12 символов")
        if len(username) > User._meta.get_field("username").max_length:
            raise CommandError("Слишком длинное имя пользователя")
        if User.objects.filter(username=username).exists():
            self.stdout.write("Пользователь уже существует; пароль и права не изменены.")
            return

        user = User(username=username, email_verified=True)
        try:
            validate_password(password, user=user)
        except PasswordValidationError as error:
            raise CommandError("Пароль не соответствует требованиям: " + "; ".join(error.messages)) from error

        # ПРОБЛЕМА: рестарт контейнера не должен повторно создавать или переписывать пароль.
        # РЕШЕНИЕ: транзакционная проверка и создание; существующего пользователя не трогаем.
        with transaction.atomic():
            if User.objects.select_for_update().filter(username=username).exists():
                return
            user.set_password(password)
            user.save()
        self.stdout.write("Первый аккаунт создан. Удалите BOOTSTRAP_* из Render Environment.")
