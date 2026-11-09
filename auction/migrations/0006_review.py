from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("auction", "0005_workflow"),
    ]

    operations = [
        migrations.CreateModel(
            name="Review",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("rating", models.PositiveSmallIntegerField()),
                ("comment", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("auction", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="review", to="auction.auction")),
                ("performer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reviews_received", to=settings.AUTH_USER_MODEL)),
                ("reviewer", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="reviews_written", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at", "-pk"]},
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(
                condition=models.Q(("rating__gte", 1), ("rating__lte", 5)),
                name="review_rating_between_1_and_5",
            ),
        ),
        migrations.AddConstraint(
            model_name="review",
            constraint=models.CheckConstraint(
                condition=models.Q(("reviewer", models.F("performer")), _negated=True),
                name="reviewer_is_not_performer",
            ),
        ),
    ]
