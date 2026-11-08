"""User KPIs and superuser analytics from the real PostgreSQL records.

Closed auction != completed work: a distinct TaskCompletion record is required.
Money is represented as integer kopecks to avoid floating-point errors.
"""
import csv
from datetime import datetime
from io import StringIO

from django.db import IntegrityError, transaction
from django.db.models import Count, Sum, Q, F
from django.db.models.functions import TruncMonth
from django.http import HttpResponse
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from auction.models import Auction, Bid, Category, User, TaskCompletion


def require_admin(user):
    if not (user.is_authenticated and user.is_active and user.is_superuser):
        raise PermissionDenied("Только администратор может просматривать статистику платформы")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_statistics(request):
    user = request.user
    if not user.is_active:
        raise PermissionDenied("Аккаунт заблокирован")
    bids = Bid.objects.filter(bidder=user)
    wins = Auction.objects.filter(status=Auction.Status.CLOSED, winner=user)
    return Response({
        "bids_count": bids.count(),
        "wins_count": wins.count(),
        "completed_tasks_count": TaskCompletion.objects.filter(
            auction__winner=user,
            auction__status=Auction.Status.CLOSED,
        ).count(),
        "active_bids_count": bids.filter(auction__status=Auction.Status.OPEN).count(),
        "auctions_created_count": Auction.objects.filter(owner=user).count(),
        "auctions_closed_count": Auction.objects.filter(owner=user, status=Auction.Status.CLOSED).count(),
        "win_rate_percent": round(wins.count() * 100 / bids.count(), 1) if bids.exists() else 0,
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def confirm_task_completion(request, auction_id):
    # The owner confirms actual delivered work; no one can silently mark their own bid complete.
    with transaction.atomic():
        auction = Auction.objects.select_for_update().filter(pk=auction_id).first()
        if auction is None:
            from django.http import Http404
            raise Http404()
        if not request.user.is_active or request.user.pk != auction.owner_id:
            raise PermissionDenied("Подтвердить выполнение может только заказчик")
        if auction.status != Auction.Status.CLOSED or auction.winner_id is None:
            raise ValidationError({"detail": "Нужен завершённый аукцион с победителем"})
        completion, created = TaskCompletion.objects.get_or_create(
            auction=auction,
            defaults={"confirmed_by": request.user},
        )
    return Response({
        "auction_id": auction.pk,
        "completed": True,
        "completed_at": completion.completed_at.isoformat(),
        "created": created,
    }, status=201 if created else 200)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def completion_status(request, auction_id):
    auction = Auction.objects.filter(pk=auction_id).first()
    if auction is None:
        from django.http import Http404
        raise Http404()
    if (request.user.pk not in (auction.owner_id, auction.winner_id)
            and not request.user.is_superuser
            and auction.status not in (Auction.Status.OPEN, Auction.Status.CLOSED)):
        from django.http import Http404
        raise Http404()
    completion = TaskCompletion.objects.filter(auction_id=auction_id).first()
    return Response({
        "auction_id": auction_id,
        "completed": completion is not None,
        "completed_at": completion.completed_at.isoformat() if completion else None,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_analytics(request):
    require_admin(request.user)
    auctions = Auction.objects.all()
    bids = Bid.objects.all()
    closed = auctions.filter(status=Auction.Status.CLOSED)
    totals = closed.aggregate(
        payment_total_kopecks=Sum("payment_kopecks"),
        budgets_total_kopecks=Sum("budget_kopecks"),
    )
    status_counts = {row["status"]: row["count"] for row in auctions.values("status").annotate(count=Count("id"))}
    category_rows = (
        auctions.values("category_id", "category__name")
        .annotate(count=Count("id"), bids_count=Count("bids"))
        .order_by("-count", "category__name")[:12]
    )
    # Trend uses closed_at, which is the event time of the completed auction.
    monthly_rows = (
        closed.exclude(closed_at__isnull=True)
        .annotate(month=TruncMonth("closed_at"))
        .values("month")
        .annotate(count=Count("id"), payment_kopecks=Sum("payment_kopecks"))
        .order_by("month")
    )
    monthly = [
        {"month": row["month"].strftime("%Y-%m"), "closed_count": row["count"],
         "payment_kopecks": row["payment_kopecks"] or 0}
        for row in monthly_rows
    ]
    return Response({
        "summary": {
            "users_total": User.objects.count(),
            "users_active": User.objects.filter(is_active=True).count(),
            "auctions_total": auctions.count(),
            "auctions_open": status_counts.get("open", 0),
            "auctions_review": status_counts.get("review", 0),
            "auctions_closed": status_counts.get("closed", 0),
            "bids_total": bids.count(),
            "unique_bidders": bids.values("bidder_id").distinct().count(),
            "auctions_with_bids": bids.values("auction_id").distinct().count(),
            "completed_tasks": TaskCompletion.objects.count(),
            "payment_total_kopecks": totals["payment_total_kopecks"] or 0,
            "budgets_closed_total_kopecks": totals["budgets_total_kopecks"] or 0,
        },
        "by_status": [{"status": s, "count": status_counts.get(s, 0)} for s in Auction.Status.values],
        "by_category": [
            {"category_id": r["category_id"], "category": r["category__name"],
             "count": r["count"], "bids_count": r["bids_count"]}
            for r in category_rows
        ],
        "by_month": monthly,
        "generated_at": timezone.now().isoformat(),
    })


def csv_cell(value):
    # Prevent spreadsheet formula injection in user-entered text.
    if value is None:
        return ""
    text = str(value)
    if text.lstrip().startswith(("=", "+", "-", "@")) or text[:1] in ("\t", "\r", "\n"):
        return "'" + text
    return text


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def admin_export_csv(request):
    require_admin(request.user)
    kind = request.query_params.get("kind", "auctions")
    if kind not in ("auctions", "users", "bids"):
        raise ValidationError({"kind": "Допустимые отчёты: auctions, users, bids"})
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="rea_' + kind + '_report.csv"'
    response.write("\ufeff")  # Excel UTF-8 BOM
    writer = csv.writer(response)
    if kind == "users":
        writer.writerow(["ID", "Логин", "Email", "Активен", "Администратор", "Зарегистрирован", "Ставок", "Побед", "Выполнено"])
        users = User.objects.annotate(
            bids_total=Count("bid", distinct=True),
            wins_total=Count("wins", filter=Q(wins__status=Auction.Status.CLOSED), distinct=True),
            completed_total=Count("wins__completion", distinct=True),
        ).order_by("id")
        for u in users.iterator():
            writer.writerow([csv_cell(v) for v in (
                u.id, u.username, u.email, u.is_active, u.is_superuser,
                u.date_joined.isoformat(), u.bids_total, u.wins_total, u.completed_total,
            )])
    elif kind == "bids":
        writer.writerow(["ID ставки", "ID аукциона", "Аукцион", "Участник", "Сумма (коп.)", "Дата"])
        for bid in Bid.objects.select_related("auction", "bidder").order_by("id").iterator():
            writer.writerow([csv_cell(v) for v in (
                bid.id, bid.auction_id, bid.auction.title, bid.bidder.username,
                bid.amount_kopecks, bid.created_at.isoformat(),
            )])
    else:
        writer.writerow(["ID", "Название", "Категория", "Заказчик", "Статус", "Бюджет (коп.)", "Число ставок", "Победитель", "Цена (коп.)", "Выполнено", "Завершение торгов"])
        auctions = Auction.objects.select_related("category", "owner", "winner").annotate(
            bid_count=Count("bids"),
        ).order_by("id")
        completed_ids = set(TaskCompletion.objects.values_list("auction_id", flat=True))
        for a in auctions.iterator():
            writer.writerow([csv_cell(v) for v in (
                a.id, a.title, a.category.name, a.owner.username, a.status,
                a.budget_kopecks, a.bid_count, a.winner.username if a.winner else "",
                a.payment_kopecks, a.id in completed_ids,
                a.closed_at.isoformat() if a.closed_at else "",
            )])
    return response
