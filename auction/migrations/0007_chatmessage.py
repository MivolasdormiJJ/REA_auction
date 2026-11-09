from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("auction", "0006_review"),
    ]

    operations = [
        migrations.CreateModel(
            name="ChatMessage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("body", models.TextField()),
                ("idempotency_key", models.CharField(max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("auction", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="chat_messages", to="auction.auction")),
                ("sender", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="chat_messages_sent", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["id"]},
        ),
        migrations.AddIndex(
            model_name="chatmessage",
            index=models.Index(fields=["auction", "id"], name="chat_auction_id_idx"),
        ),
        migrations.AddConstraint(
            model_name="chatmessage",
            constraint=models.UniqueConstraint(
                fields=("auction", "sender", "idempotency_key"),
                name="chat_unique_sender_request",
            ),
        ),
    ]
