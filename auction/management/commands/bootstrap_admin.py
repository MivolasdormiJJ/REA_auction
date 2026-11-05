"""Provision a one-time administrator using a secret stored in Render.

No default credentials and no password resets. Remove ADMIN_BOOTSTRAP_PASSWORD
from Render immediately after the first successful deployment.
"""
import os
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from auction.models import User


class Command(BaseCommand):
    help = "Provision one admin account only if a secure bootstrap secret is provided"

    def handle(self, *args, **kwargs):
        password = os.environ.get("ADMIN_BOOTSTRAP_PASSWORD", "")
        if not password:
            return
        name = os.environ.get("ADMIN_BOOTSTRAP_USERNAME", "rea_admin").strip()
        email = os.environ.get("ADMIN_BOOTSTRAP_EMAIL", "rea_admin@example.invalid").strip()
        if not name or not email:
            raise CommandError("Admin username and email must be nonempty")
        if User.objects.filter(username=name).exists():
            self.stdout.write("Admin bootstrap: account already exists, unchanged")
            return
        account = User(username=name, email=email, email_verified=True, is_staff=True, is_superuser=True)
        try:
            validate_password(password, user=account)
        except ValidationError as exc:
            raise CommandError("Admin password does not meet Django security requirements") from exc
        with transaction.atomic():
            if User.objects.select_for_update().filter(username=name).exists():
                return
            account.set_password(password)
            account.save()
        self.stdout.write("Administrator successfully provisioned; clear ADMIN_BOOTSTRAP_PASSWORD")
