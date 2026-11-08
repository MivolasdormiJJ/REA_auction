from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q


class User(AbstractUser):
    email = models.EmailField(unique=True)
    email_verified = models.BooleanField(default=False)


class Category(models.Model):
    name = models.CharField(max_length=80, unique=True)


class Auction(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft"
        REVIEW = "review"
        REJECTED = "rejected"
        OPEN = "open"
        CLOSED = "closed"
        PAUSED = "paused"

    owner = models.ForeignKey(User, on_delete=models.PROTECT, related_name="auctions")
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    title = models.CharField(max_length=150)
    description = models.TextField()
    budget_kopecks = models.PositiveBigIntegerField()
    ends_at = models.DateTimeField()
    due_at = models.DateTimeField()
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.DRAFT
    )
    moderation_reason = models.TextField(blank=True)
    winner = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, related_name="wins"
    )
    payment_kopecks = models.PositiveBigIntegerField(null=True)
    closed_at = models.DateTimeField(null=True)

    class Meta:
        permissions = [("moderate_auction", "Модерировать аукционы")]
        indexes = [models.Index(fields=["status", "ends_at"])]
        constraints = [
            models.CheckConstraint(
                condition=Q(budget_kopecks__gte=100), name="budget_min_ruble"
            ),
            models.CheckConstraint(
                condition=Q(due_at__gt=models.F("ends_at")), name="due_after_auction"
            ),
        ]


class Bid(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.PROTECT, related_name="bids")
    bidder = models.ForeignKey(User, on_delete=models.PROTECT)
    amount_kopecks = models.PositiveBigIntegerField()
    idempotency_key = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["auction", "bidder"], name="one_bid_per_person"
            ),
            models.UniqueConstraint(
                fields=["auction", "bidder", "idempotency_key"],
                name="unique_request_key",
            ),
            models.CheckConstraint(
                condition=Q(amount_kopecks__gte=1), name="bid_positive"
            ),
        ]


class Event(models.Model):
    auction = models.ForeignKey(Auction, on_delete=models.PROTECT)
    actor = models.ForeignKey(User, on_delete=models.PROTECT, null=True)
    action = models.CharField(max_length=40)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuctionRequest(models.Model):
    # ПРОБЛЕМА: повтор POST после потери ответа создавал второй заказ.
    # РЕШЕНИЕ: уникальный ключ заказчика хранит результат первой операции.
    owner = models.ForeignKey(User, on_delete=models.PROTECT)
    idempotency_key = models.CharField(max_length=80)
    payload_hash = models.CharField(max_length=64)
    auction = models.ForeignKey(Auction, on_delete=models.PROTECT)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["owner", "idempotency_key"], name="unique_auction_create_key")]

# Import the completion model so Django migration autodiscovery registers it.
from .task_completion import TaskCompletion  # noqa: E402,F401


class WorkOrder(models.Model):
    """Post-auction fulfillment; separate from the bidding lifecycle."""

    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "В работе"
        SUBMITTED = "submitted", "На приёмке"
        REVISION_REQUESTED = "revision_requested", "На доработке"
        ACCEPTED = "accepted", "Принято"

    auction = models.OneToOneField(Auction, on_delete=models.PROTECT, related_name="work_order")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)


class WorkSubmission(models.Model):
    """Immutable delivery text with an auditable review for each iteration."""

    class Review(models.TextChoices):
        PENDING = "pending", "На проверке"
        REVISION = "revision", "Доработать"
        ACCEPTED = "accepted", "Принято"

    order = models.ForeignKey(WorkOrder, on_delete=models.PROTECT, related_name="submissions")
    revision_number = models.PositiveIntegerField()
    idempotency_key = models.CharField(max_length=80)
    result_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    review_status = models.CharField(max_length=10, choices=Review.choices, default=Review.PENDING)
    feedback = models.TextField(blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["revision_number"]
        constraints = [
            models.UniqueConstraint(fields=["order", "revision_number"], name="work_unique_revision"),
            models.UniqueConstraint(fields=["order", "idempotency_key"], name="work_unique_submission_key"),
        ]
