from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("auction", "0004_task_completion")]

    operations = [
        migrations.CreateModel(
            name="WorkOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("in_progress", "В работе"), ("submitted", "На приёмке"), ("revision_requested", "На доработке"), ("accepted", "Принято")], default="in_progress", max_length=20)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("accepted_at", models.DateTimeField(blank=True, null=True)),
                ("auction", models.OneToOneField(on_delete=django.db.models.deletion.PROTECT, related_name="work_order", to="auction.auction")),
            ],
        ),
        migrations.CreateModel(
            name="WorkSubmission",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("revision_number", models.PositiveIntegerField()),
                ("idempotency_key", models.CharField(max_length=80)),
                ("result_text", models.TextField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("review_status", models.CharField(choices=[("pending", "На проверке"), ("revision", "Доработать"), ("accepted", "Принято")], default="pending", max_length=10)),
                ("feedback", models.TextField(blank=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="submissions", to="auction.workorder")),
            ],
            options={"ordering": ["revision_number"]},
        ),
        migrations.AddConstraint(
            model_name="worksubmission",
            constraint=models.UniqueConstraint(fields=("order", "revision_number"), name="work_unique_revision"),
        ),
        migrations.AddConstraint(
            model_name="worksubmission",
            constraint=models.UniqueConstraint(fields=("order", "idempotency_key"), name="work_unique_submission_key"),
        ),
    ]
