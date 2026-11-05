"""Operations for the superuser, including every account and auction."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from auction.models import Auction, AuctionRequest, Bid, Category, Event, User


@admin.register(User)
class AccountAdmin(UserAdmin):
    list_display = ("username", "email", "email_verified", "is_active", "is_staff", "is_superuser", "date_joined")
    list_filter = ("is_active", "email_verified", "is_staff", "is_superuser")
    search_fields = ("username", "email")
    fieldsets = UserAdmin.fieldsets + (("Проверка аккаунта", {"fields": ("email_verified",)}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Email", {"fields": ("email", "email_verified")}),)


@admin.register(Auction)
class AuctionAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "owner", "status", "budget_kopecks", "ends_at", "winner")
    list_filter = ("status", "category")
    search_fields = ("title", "owner__username")
    list_select_related = ("owner", "category")
    raw_id_fields = ("owner", "winner")


@admin.register(Bid)
class BidAdmin(admin.ModelAdmin):
    list_display = ("id", "auction", "bidder", "amount_kopecks", "created_at")
    list_select_related = ("auction", "bidder")
    search_fields = ("auction__title", "bidder__username")


admin.site.register(Category)
admin.site.register(Event)
admin.site.register(AuctionRequest)
