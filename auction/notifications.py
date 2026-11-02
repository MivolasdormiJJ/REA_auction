"""Auction result notifications, derived from the final auction state.

No separate read/unread persistence is claimed: each closed auction with a bid
produces one durable result for the bidding account.
"""
from django.db.models import Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auction.models import Bid, Auction


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
    items.sort(key=lambda item: item["created_at"] or "", reverse=True)
    return Response({"count": len(items), "results": items})
