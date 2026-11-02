"""Маршруты API аукциона и аутентификации."""

from django.urls import include, path, re_path
from django.conf import settings
from django.http import FileResponse, Http404
from rest_framework.routers import DefaultRouter
from auction.admin_api import AllUsersViewSet, AllAuctionsViewSet

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
    path("api/", include(router.urls)),
    path("api/auth/csrf/", csrf),
    path("api/auth/login/", signin),
    path("api/auth/logout/", signout),
    path("api/auth/me/", me),
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
        re_path(r"^(?!api/|api-auth/|static/|assets/|favicon\\.ico).*$", frontend_app),
    ]
