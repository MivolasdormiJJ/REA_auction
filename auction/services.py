from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, PermissionDenied, ValidationError

from .models import Auction, Bid, Event, User

Status = Auction.Status

EDITABLE_STATUSES = (Status.DRAFT, Status.REJECTED)


class Conflict(APIException):
    status_code = 409
    default_detail = "Конфликт состояния"


class Locked(APIException):
    status_code = 423
    default_detail = "Аукцион приостановлен"


def eligible(user):
    if not user.is_active or not user.email_verified:
        raise PermissionDenied(
            "Требуется активная учётная запись с подтверждённой почтой"
        )


def event(auction, actor, action, reason=""):
    Event.objects.create(auction=auction, actor=actor, action=action, reason=reason)


@transaction.atomic
def place_bid(auction_id, user, amount, key):
    auction = Auction.objects.select_for_update().get(pk=auction_id)
    # Пользователь повторно читается внутри транзакции; блокировка не берётся
    # по пользователю, чтобы избежать взаимной блокировки разных аукционов.
    eligible(User.objects.get(pk=user.pk))
    if auction.owner_id == user.pk:
        raise PermissionDenied("Нельзя ставить на свою задачу")

    previous = Bid.objects.filter(
        auction=auction,
        bidder=user,
        idempotency_key=key,
    ).first()
    if previous:
        if previous.auction_id != auction.pk or previous.amount_kopecks != amount:
            raise Conflict("Ключ уже использован с другим телом запроса")
        return previous, False

    if auction.status != Status.OPEN or timezone.now() >= auction.ends_at:
        raise Conflict("Приём ставок закрыт")
    if amount > auction.budget_kopecks:
        raise ValidationError({"amount_kopecks": "Ставка превышает бюджет"})
    if Bid.objects.filter(auction=auction, bidder=user).exists():
        raise Conflict("Разрешена одна неизменяемая ставка на участника")

    bid = Bid.objects.create(
        auction=auction,
        bidder=user,
        amount_kopecks=amount,
        idempotency_key=key,
    )
    event(auction, user, "bid_accepted")
    return bid, True


@transaction.atomic
def transition(auction_id, user, action, reason=""):
    auction = Auction.objects.select_for_update().get(pk=auction_id)
    eligible(User.objects.get(pk=user.pk))
    if action == "submit":
        if auction.owner_id != user.pk:
            raise PermissionDenied()
        if auction.status not in EDITABLE_STATUSES:
            raise Conflict()
        target = Status.REVIEW
    else:
        if not user.has_perm("auction.moderate_auction") or auction.owner_id == user.pk:
            raise PermissionDenied("Нельзя модерировать свою задачу")
        if auction.status != Status.REVIEW:
            raise Conflict()
        if not reason.strip():
            raise ValidationError({"reason": "Укажите причину решения"})
        target = Status.OPEN if action == "approve" else Status.REJECTED

    if target in (Status.REVIEW, Status.OPEN) and (
        auction.ends_at <= timezone.now() or auction.due_at <= auction.ends_at
    ):
        raise ValidationError("Проверьте сроки")

    auction.status = target
    auction.moderation_reason = reason
    auction.save(update_fields=["status", "moderation_reason"])
    event(auction, user, action, reason)
    return auction


@transaction.atomic
def close_auction(auction_id):
    auction = Auction.objects.select_for_update().get(pk=auction_id)
    if auction.status != Status.OPEN or timezone.now() < auction.ends_at:
        return auction

    # Исключение участника меняет вторую цену. Вместо тихого перерасчёта
    # останавливаем торги и сохраняем историю для решения следующего спринта.
    if (
        not auction.owner.is_active
        or not auction.owner.email_verified
        or auction.bids.filter(_invalid_bidder_filter()).exists()
    ):
        auction.status = Status.PAUSED
        auction.save(update_fields=["status"])
        event(auction, None, "paused", "Участник заблокирован или допуск отозван")
        return auction

    best = list(auction.bids.order_by("amount_kopecks", "created_at", "id")[:2])
    auction.status = Status.CLOSED
    auction.closed_at = timezone.now()
    if best:
        auction.winner_id = best[0].bidder_id
        auction.payment_kopecks = (
            best[1].amount_kopecks if len(best) > 1 else auction.budget_kopecks
        )
    auction.save(update_fields=["status", "closed_at", "winner", "payment_kopecks"])
    event(auction, None, "closed")
    return auction


def _invalid_bidder_filter():
    return Q(bidder__is_active=False) | Q(bidder__email_verified=False)
