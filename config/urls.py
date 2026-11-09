"""Маршруты API аукциона и аутентификации."""

from django.urls import include, path, re_path
from django.contrib import admin
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.routers import DefaultRouter
from auction.admin_api import AllUsersViewSet, AllAuctionsViewSet
from auction.notifications import my_notifications
from auction.my_works import my_works
from auction.work_api import work_detail, work_start, work_submit, work_request_revision, work_accept
from auction.reviews_api import create_review, performer_reputation
from auction.chat_api import auction_chat
from auction.analytics import my_statistics, confirm_task_completion, completion_status, admin_analytics, admin_export_csv

from auction.views import (
    AuctionViewSet,
    CategoryViewSet,
    csrf,
    me,
    signin,
    signout,
    register,
    verify_email,
)

router = DefaultRouter()
router.register("auctions", AuctionViewSet, basename="auctions")
router.register("categories", CategoryViewSet)
router.register("admin/users", AllUsersViewSet, basename="admin-users")
router.register("admin/auctions", AllAuctionsViewSet, basename="admin-auctions")

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("api/", include(router.urls)),
    path("api/auth/csrf/", csrf),
    path("api/auth/login/", signin),
    path("api/auth/logout/", signout),
    path("api/auth/me/", me),
    path("api/notifications/", my_notifications),
    path("api/my/works/", my_works),
    path("api/auctions/<int:auction_id>/work/", work_detail),
    path("api/auctions/<int:auction_id>/work/start/", work_start),
    path("api/auctions/<int:auction_id>/work/submit/", work_submit),
    path("api/auctions/<int:auction_id>/work/request-revision/", work_request_revision),
    path("api/auctions/<int:auction_id>/work/accept/", work_accept),
    path("api/auctions/<int:auction_id>/review/", create_review),
    path("api/performers/<int:user_id>/reputation/", performer_reputation),
    path("api/auctions/<int:auction_id>/chat/", auction_chat),
    path("api/my/statistics/", my_statistics),
    path("api/auctions/<int:auction_id>/complete-work/", confirm_task_completion),
    path("api/auctions/<int:auction_id>/completion/", completion_status),
    path("api/admin/analytics/", admin_analytics),
    path("api/admin/reports/", admin_export_csv),
    path("api/auth/register/", register),
    path("api/auth/verify-email/", verify_email),
]

urlpatterns += [
    path(
        "api-auth/",
        include("rest_framework.urls", namespace="rest_framework"),
    ),
]

# ПРОБЛЕМА: React Router использует /login, /profile и другие клиентские URL.
# РЕШЕНИЕ: Django отдаёт index.html для страниц SPA, не перехватывая /api или /static.
def frontend_app(request):
    index = settings.FRONTEND_DIST_DIR / "index.html"
    if not index.exists():
        raise Http404("Frontend build is missing")
    return FileResponse(index.open("rb"), content_type="text/html")


if settings.FRONTEND_DIST_DIR.is_dir():
    urlpatterns += [
        re_path(r"^(?!api/|api-auth/|django-admin/|static/|assets/|favicon\\.ico).*$", frontend_app),
    ]
