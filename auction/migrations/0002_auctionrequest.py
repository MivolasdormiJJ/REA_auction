from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("auction", "0001_initial"),
    ]

    operations = [
        # ПРОБЛЕМА: без записи ключа идемпотентности нельзя отличить повтор заказа.
        # РЕШЕНИЕ: отдельная таблица связывает уникальный ключ пользователя с аукционом.
        migrations.CreateModel(
            name="AuctionRequest",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("idempotency_key", models.CharField(max_length=80)),
                ("payload_hash", models.CharField(max_length=64)),
                ("auction", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to="auction.auction")),
                ("owner", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddConstraint(
            model_name="auctionrequest",
            constraint=models.UniqueConstraint(fields=("owner", "idempotency_key"), name="unique_auction_create_key"),
        ),
    ]
