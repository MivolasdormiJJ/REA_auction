"""Private, immutable post-auction chat for the customer and winner."""
from django.db import transaction
from django.http import Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auction.models import Auction, ChatMessage
from auction.services import Conflict, event


MAX_MESSAGE_LENGTH = 2000
PAGE_SIZE = 100


def check_chat_access(auction, user, *, sending=False):
    if not user.is_active or not user.email_verified:
        raise PermissionDenied("Нет доступа к чату")
    if auction.status != Auction.Status.CLOSED or auction.winner_id is None:
        raise Conflict("Чат доступен после завершения торгов с победителем")
    participant = user.pk in (auction.owner_id, auction.winner_id)
    if not participant and not (user.is_superuser and not sending):
        raise Http404()


def serialize_message(message):
    return {
        "id": message.pk,
        "auction_id": message.auction_id,
        "sender_id": message.sender_id,
        "sender_username": message.sender.username,
        "body": message.body,
        "created_at": message.created_at.isoformat(),
    }


def chat_payload(auction, messages):
    return {
        "auction_id": auction.pk,
        "owner": {"id": auction.owner_id, "username": auction.owner.username},
        "winner": {"id": auction.winner_id, "username": auction.winner.username},
        "results": [serialize_message(message) for message in messages],
    }


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def auction_chat(request, auction_id):
    if request.method == "GET":
        auction = (Auction.objects.select_related("owner", "winner")
                   .filter(pk=auction_id).first())
        if auction is None:
            raise Http404()
        check_chat_access(auction, request.user)
        after = request.query_params.get("after")
        messages = ChatMessage.objects.filter(auction=auction).select_related("sender")
        if after is not None:
            if not after.isdecimal():
                raise ValidationError({"after": "Требуется идентификатор сообщения"})
            messages = list(messages.filter(pk__gt=int(after)).order_by("id")[:PAGE_SIZE])
        else:
            messages = list(messages.order_by("-id")[:PAGE_SIZE])
            messages.reverse()
        return Response(chat_payload(auction, messages))

    body = request.data.get("body")
    if not isinstance(body, str) or not 1 <= len(body.strip()) <= MAX_MESSAGE_LENGTH:
        raise ValidationError({"body": f"Сообщение должно содержать от 1 до {MAX_MESSAGE_LENGTH} символов"})
    text = body.strip()
    key = request.headers.get("Idempotency-Key", "")
    if not isinstance(key, str) or not key.strip() or len(key) > 80:
        raise ValidationError({"Idempotency-Key": "Передайте ключ запроса длиной до 80 символов"})

    with transaction.atomic():
        # Lock only the auction row. Joining the nullable winner under
        # FOR UPDATE is rejected by PostgreSQL.
        auction = Auction.objects.select_for_update().filter(pk=auction_id).first()
        if auction is None:
            raise Http404()
        check_chat_access(auction, request.user, sending=True)
        old = ChatMessage.objects.filter(
            auction=auction, sender=request.user, idempotency_key=key,
        ).select_related("sender").first()
        if old is not None:
            if old.body != text:
                raise Conflict("Ключ уже использован для другого сообщения")
            return Response(serialize_message(old))
        message = ChatMessage.objects.create(
            auction=auction,
            sender=request.user,
            body=text,
            idempotency_key=key,
        )
        event(auction, request.user, "chat_message_sent")
        message = ChatMessage.objects.select_related("sender").get(pk=message.pk)
    return Response(serialize_message(message), status=201)
