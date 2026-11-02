"""Read-only management data for staff accounts."""
from rest_framework import permissions, viewsets
from auction.models import User, Auction
from auction.serializers import AdminUserSerializer, AuctionSerializer


class Administrator(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.is_active and request.user.is_superuser)


class AllUsersViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [Administrator]
    serializer_class = AdminUserSerializer
    queryset = User.objects.order_by("-id")


class AllAuctionsViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [Administrator]
    serializer_class = AuctionSerializer
    queryset = Auction.objects.order_by("-id")
