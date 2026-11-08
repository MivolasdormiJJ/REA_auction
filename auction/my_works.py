"""Private, paginated portfolio of orders won by the current user."""
from django.db.models import Exists, OuterRef
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auction.models import Auction, TaskCompletion, WorkOrder


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_works(request):
    user = request.user
    if not user.is_active or not user.email_verified:
        raise PermissionDenied("Нет доступа к списку работ")
    category = request.query_params.get("status", "active")
    if category not in ("active", "accepted"):
        raise ValidationError({"status": "Выберите active или accepted"})

    # A completed job is defined by a confirmed acceptance, never merely by closing bids.
    works = (Auction.objects.filter(winner=user, status=Auction.Status.CLOSED)
        .annotate(has_completion=Exists(
            TaskCompletion.objects.filter(auction_id=OuterRef("pk"))
        ))
        .select_related("category", "work_order")
        .order_by("-closed_at", "-pk"))
    works = works.filter(has_completion=(category == "accepted"))
    paginator = PageNumberPagination()
    paginator.page_size = 12
    page = paginator.paginate_queryset(works, request)
    rows = []
    for auction in page:
        order = getattr(auction, "work_order", None)
        if auction.has_completion:
            status = "accepted"
        elif order is None:
            status = "not_started"
        else:
            status = order.status
        latest = (order.submissions.order_by("-revision_number").first()
                  if order else None)
        rows.append({
            "auction_id": auction.pk,
            "title": auction.title,
            "description": auction.description,
            "category": auction.category.name,
            "status": status,
            "payment_kopecks": auction.payment_kopecks,
            "due_at": auction.due_at.isoformat(),
            "closed_at": auction.closed_at.isoformat() if auction.closed_at else None,
            "accepted_at": (
                order.accepted_at.isoformat()
                if order and order.accepted_at else None
            ),
            "is_overdue": status != "accepted" and timezone.now() > auction.due_at,
            "latest_result": latest.result_text if latest else None,
            "latest_feedback": latest.feedback if latest else None,
            "latest_revision": latest.revision_number if latest else None,
        })
    return paginator.get_paginated_response(rows)
