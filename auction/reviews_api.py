"""Authenticated performer reputation and post-acceptance customer reviews."""
from django.db import transaction
from django.db.models import Avg, Count
from django.http import Http404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auction.models import Auction, Review, TaskCompletion, User
from auction.services import Conflict, event


def serialize_review(review):
    return {
        "id": review.pk,
        "auction_id": review.auction_id,
        "auction_title": review.auction.title,
        "reviewer_username": review.reviewer.username,
        "performer_id": review.performer_id,
        "rating": review.rating,
        "comment": review.comment,
        "created_at": review.created_at.isoformat(),
    }


def require_admitted(user):
    if not user.is_active or not user.email_verified:
        raise PermissionDenied("Нет доступа к отзывам")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def performer_reputation(request, user_id):
    require_admitted(request.user)
    performer = User.objects.filter(pk=user_id, is_active=True).first()
    if performer is None:
        raise Http404()
    reviews = (Review.objects.filter(performer=performer)
               .select_related("auction", "reviewer")
               .order_by("-created_at", "-pk"))
    totals = reviews.aggregate(average=Avg("rating"), count=Count("id"))
    distribution = {str(score): 0 for score in range(1, 6)}
    for row in reviews.values("rating").annotate(count=Count("id")):
        distribution[str(row["rating"])] = row["count"]
    return Response({
        "performer": {"id": performer.pk, "username": performer.username},
        "average_rating": round(float(totals["average"]), 1) if totals["average"] is not None else None,
        "reviews_count": totals["count"],
        "completed_tasks_count": TaskCompletion.objects.filter(
            auction__winner=performer, auction__status=Auction.Status.CLOSED,
        ).count(),
        "wins_count": Auction.objects.filter(
            winner=performer, status=Auction.Status.CLOSED,
        ).count(),
        "rating_distribution": distribution,
        "reviews": [serialize_review(review) for review in reviews[:20]],
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_review(request, auction_id):
    require_admitted(request.user)
    rating = request.data.get("rating")
    comment = request.data.get("comment")
    if isinstance(rating, bool) or not isinstance(rating, int) or not 1 <= rating <= 5:
        raise ValidationError({"rating": "Поставьте оценку от 1 до 5"})
    if not isinstance(comment, str) or not 20 <= len(comment.strip()) <= 2000:
        raise ValidationError({"comment": "Комментарий должен содержать от 20 до 2000 символов"})

    with transaction.atomic():
        auction = (Auction.objects.select_for_update()
                   .select_related("owner", "winner")
                   .filter(pk=auction_id).first())
        if auction is None:
            raise Http404()
        if auction.owner_id != request.user.pk:
            raise PermissionDenied("Оставить отзыв может только заказчик")
        if auction.status != Auction.Status.CLOSED or auction.winner_id is None:
            raise Conflict("Отзыв доступен только после завершения заказа")
        if not TaskCompletion.objects.filter(auction=auction).exists():
            raise Conflict("Сначала примите выполненную работу")
        if Review.objects.filter(auction=auction).exists():
            raise Conflict("Отзыв по этому заказу уже опубликован")
        review = Review.objects.create(
            auction=auction,
            reviewer=request.user,
            performer=auction.winner,
            rating=rating,
            comment=comment.strip(),
        )
        event(auction, request.user, "review_created", f"Оценка: {rating}")
        review = Review.objects.select_related("auction", "reviewer").get(pk=review.pk)
    return Response(serialize_review(review), status=201)
