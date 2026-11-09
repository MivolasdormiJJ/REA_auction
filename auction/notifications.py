"""Auction result notifications, derived from the final auction state.

No separate read/unread persistence is claimed: each closed auction with a bid
produces one durable result for the bidding account.
"""
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auction.models import Bid, Auction, ChatMessage, WorkOrder, WorkSubmission


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_notifications(request):
    if not request.user.is_active:
        return Response({"detail": "Account inactive"}, status=403)
    # Only the caller's bids; never leak other bidders' private account details.
    bids = (Bid.objects.filter(bidder=request.user, auction__status=Auction.Status.CLOSED)
            .select_related("auction").order_by("-auction__closed_at", "-id"))
    items = []
    for bid in bids:
        a = bid.auction
        won = a.winner_id == request.user.id
        items.append({
            "id": "auction-result-" + str(a.id),
            "auction_id": a.id,
            "auction_title": a.title,
            "type": "auction_won" if won else "auction_lost",
            "title": "Вы победили в аукционе!" if won else "Аукцион завершён — победил другой участник",
            "message": ("Ваша ставка оказалась лучшей. Итоговая цена определена по правилу второй цены."
                        if won else "Спасибо за участие. В этом аукционе выбрана более выгодная ставка."),
            "your_bid_kopecks": bid.amount_kopecks,
            "payment_kopecks": a.payment_kopecks if won else None,
            "created_at": a.closed_at.isoformat() if a.closed_at else None,
        })
    # Owners have a separate notification when their task reaches a result.
    owned = (Auction.objects.filter(owner=request.user, status=Auction.Status.CLOSED)
             .order_by("-closed_at", "-id"))
    for a in owned:
        items.append({
            "id": "auction-owner-result-" + str(a.id),
            "auction_id": a.id, "auction_title": a.title,
            "type": "auction_owner_closed",
            "title": "Торги по вашей задаче завершены",
            "message": ("Победитель определён, можно посмотреть результат."
                        if a.winner_id else "Торги завершились без предложений."),
            "your_bid_kopecks": None,
            "payment_kopecks": a.payment_kopecks,
            "created_at": a.closed_at.isoformat() if a.closed_at else None,
        })
    # Fulfillment updates are derived from durable work and review records.
    orders = WorkOrder.objects.filter(
        auction__status=Auction.Status.CLOSED
    ).filter(Q(auction__owner=request.user) | Q(auction__winner=request.user)).select_related("auction").prefetch_related("submissions")
    for order in orders:
        a = order.auction
        for submission in order.submissions.all():
            if a.owner_id == request.user.pk:
                items.append({
                    "id": f"work-submission-{submission.id}-owner",
                    "auction_id": a.id, "auction_title": a.title,
                    "type": "work_submitted",
                    "title": "Работа передана на приёмку",
                    "message": f"Исполнитель отправил версию {submission.revision_number}. Проверьте результат.",
                    "your_bid_kopecks": None, "payment_kopecks": None,
                    "created_at": submission.created_at.isoformat(),
                })
            elif a.winner_id == request.user.pk and submission.reviewed_at is not None:
                accepted = submission.review_status == WorkSubmission.Review.ACCEPTED
                items.append({
                    "id": f"work-review-{submission.id}-winner",
                    "auction_id": a.id, "auction_title": a.title,
                    "type": "work_accepted" if accepted else "work_revision",
                    "title": "Работа принята" if accepted else "Заказчик запросил доработку",
                    "message": "Результат принят заказчиком." if accepted else
                        "Заказчик оставил замечания. Откройте карточку для новой версии.",
                    "your_bid_kopecks": None, "payment_kopecks": None,
                    "created_at": submission.reviewed_at.isoformat(),
                })
    # A recipient sees incoming chat messages as durable notifications.
    incoming_messages = (ChatMessage.objects.filter(
        Q(auction__owner=request.user) | Q(auction__winner=request.user)
    ).exclude(sender=request.user).select_related("auction", "sender").order_by("-created_at")[:50])
    for chat_message in incoming_messages:
        items.append({
            "id": f"chat-message-{chat_message.id}",
            "auction_id": chat_message.auction_id,
            "auction_title": chat_message.auction.title,
            "type": "chat_message",
            "title": f"Новое сообщение от {chat_message.sender.username}",
            "message": chat_message.body[:160],
            "your_bid_kopecks": None,
            "payment_kopecks": None,
            "created_at": chat_message.created_at.isoformat(),
        })
    items.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return Response({"count": len(items), "results": items})
