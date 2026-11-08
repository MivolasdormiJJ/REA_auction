"""Fulfillment flow after a reverse auction: work -> submission -> review -> acceptance.

All transitions are transactional and locked per auction. Owners cannot deliver,
winners cannot accept, and repeated deliveries have stable idempotency keys.
"""
from django.db import transaction
from django.http import Http404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auction.models import Auction, TaskCompletion, WorkOrder, WorkSubmission
from auction.services import Conflict, event


def check_access(auction, user, actor=None):
    if not user.is_active or not user.email_verified:
        raise PermissionDenied("Нет доступа к выполнению заказа")
    if auction.status != Auction.Status.CLOSED or not auction.winner_id:
        raise Conflict("Работа доступна только после завершения торгов с победителем")
    if user.pk not in (auction.owner_id, auction.winner_id) and not user.is_superuser:
        raise Http404()
    if actor == "winner" and user.pk != auction.winner_id:
        raise PermissionDenied("Это действие доступно только победителю")
    if actor == "owner" and user.pk != auction.owner_id:
        raise PermissionDenied("Это действие доступно только заказчику")


def serialize(auction, order=None):
    completion = TaskCompletion.objects.filter(auction_id=auction.pk).first()
    if order is None:
        order = WorkOrder.objects.filter(auction_id=auction.pk).first()
    deliveries = [] if order is None else [
        {
            "id": s.pk,
            "revision_number": s.revision_number,
            "result_text": s.result_text,
            "created_at": s.created_at.isoformat(),
            "review_status": s.review_status,
            "feedback": s.feedback,
            "reviewed_at": s.reviewed_at.isoformat() if s.reviewed_at else None,
        }
        for s in order.submissions.all()
    ]
    return {
        "auction_id": auction.pk,
        "owner_id": auction.owner_id,
        "winner_id": auction.winner_id,
        "status": order.status if order else ("accepted" if completion else "not_started"),
        "started_at": order.started_at.isoformat() if order else None,
        "accepted_at": (order.accepted_at or (completion.completed_at if completion else None)).isoformat()
        if (order and order.accepted_at) or completion else None,
        "due_at": auction.due_at.isoformat(),
        "is_overdue": timezone.now() > auction.due_at and not completion,
        "submissions": deliveries,
    }


def get_locked_auction(auction_id):
    try:
        return Auction.objects.select_for_update().get(pk=auction_id)
    except Auction.DoesNotExist:
        raise Http404()


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def work_detail(request, auction_id):
    auction = Auction.objects.filter(pk=auction_id).first()
    if auction is None:
        raise Http404()
    check_access(auction, request.user)
    return Response(serialize(auction))


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def work_start(request, auction_id):
    with transaction.atomic():
        auction = get_locked_auction(auction_id)
        check_access(auction, request.user, "winner")
        if TaskCompletion.objects.filter(auction=auction).exists():
            raise Conflict("Работа уже принята")
        order, created = WorkOrder.objects.get_or_create(auction=auction)
        if created:
            event(auction, request.user, "work_started")
        payload = serialize(auction, order)
    return Response(payload, status=201 if created else 200)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def work_submit(request, auction_id):
    text = request.data.get("result_text")
    if not isinstance(text, str) or not 20 <= len(text.strip()) <= 10000:
        raise ValidationError({"result_text": "Описание результата — от 20 до 10000 символов"})
    result_text = text.strip()
    key = request.headers.get("Idempotency-Key", "")
    if not isinstance(key, str) or not key.strip() or len(key) > 80:
        raise ValidationError({"Idempotency-Key": "Передайте ключ запроса длиной до 80 символов"})
    with transaction.atomic():
        auction = get_locked_auction(auction_id)
        check_access(auction, request.user, "winner")
        order = WorkOrder.objects.select_for_update().filter(auction=auction).first()
        if order is None:
            raise Conflict("Сначала возьмите заказ в работу")
        old = WorkSubmission.objects.filter(order=order, idempotency_key=key).first()
        if old:
            if old.result_text != result_text:
                raise Conflict("Ключ уже использован для другого результата")
            return Response({"submission_id": old.pk, "replayed": True, **serialize(auction, order)})
        if order.status not in (WorkOrder.Status.IN_PROGRESS, WorkOrder.Status.REVISION_REQUESTED):
            raise Conflict("Сейчас нельзя отправить новую версию работы")
        last = WorkSubmission.objects.filter(order=order).order_by("-revision_number").first()
        submission = WorkSubmission.objects.create(
            order=order,
            revision_number=last.revision_number + 1 if last else 1,
            idempotency_key=key,
            result_text=result_text,
        )
        order.status = WorkOrder.Status.SUBMITTED
        order.save(update_fields=["status", "updated_at"])
        event(auction, request.user, "work_submitted")
        payload = serialize(auction, order)
    return Response({"submission_id": submission.pk, "replayed": False, **payload}, status=201)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def work_request_revision(request, auction_id):
    feedback = request.data.get("feedback")
    if not isinstance(feedback, str) or not 5 <= len(feedback.strip()) <= 2000:
        raise ValidationError({"feedback": "Укажите причину доработки (5–2000 символов)"})
    with transaction.atomic():
        auction = get_locked_auction(auction_id)
        check_access(auction, request.user, "owner")
        order = WorkOrder.objects.select_for_update().filter(auction=auction).first()
        if order is None or order.status != WorkOrder.Status.SUBMITTED:
            raise Conflict("На приёмке нет отправленной работы")
        submission = WorkSubmission.objects.filter(order=order).order_by("-revision_number").first()
        if submission is None or submission.review_status != WorkSubmission.Review.PENDING:
            raise Conflict("Версия уже рассмотрена")
        submission.review_status = WorkSubmission.Review.REVISION
        submission.feedback = feedback.strip()
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=["review_status", "feedback", "reviewed_at"])
        order.status = WorkOrder.Status.REVISION_REQUESTED
        order.save(update_fields=["status", "updated_at"])
        event(auction, request.user, "work_revision_requested", feedback.strip())
        payload = serialize(auction, order)
    return Response(payload)


def accept_delivered_work(auction_id, user):
    with transaction.atomic():
        auction = get_locked_auction(auction_id)
        check_access(auction, user, "owner")
        order = WorkOrder.objects.select_for_update().filter(auction=auction).first()
        if order is not None and order.status == WorkOrder.Status.ACCEPTED:
            completion = TaskCompletion.objects.get(auction=auction)
            return auction, order, completion, False
        # Existing completions created before the introduction of submissions are read-only.
        if TaskCompletion.objects.filter(auction=auction).exists():
            return auction, order, TaskCompletion.objects.get(auction=auction), False
        if order is None or order.status != WorkOrder.Status.SUBMITTED:
            raise Conflict("Принять можно только отправленную на проверку работу")
        submission = WorkSubmission.objects.filter(order=order).order_by("-revision_number").first()
        if submission is None or submission.review_status != WorkSubmission.Review.PENDING:
            raise Conflict("Версия уже рассмотрена")
        submission.review_status = WorkSubmission.Review.ACCEPTED
        submission.reviewed_at = timezone.now()
        submission.save(update_fields=["review_status", "reviewed_at"])
        order.status = WorkOrder.Status.ACCEPTED
        order.accepted_at = timezone.now()
        order.save(update_fields=["status", "accepted_at", "updated_at"])
        completion, created = TaskCompletion.objects.get_or_create(
            auction=auction, defaults={"confirmed_by": user},
        )
        event(auction, user, "work_accepted")
        return auction, order, completion, created


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def work_accept(request, auction_id):
    auction, order, completion, created = accept_delivered_work(auction_id, request.user)
    return Response(serialize(auction, order), status=201 if created else 200)
