"""Operations for the superuser, including every account and auction."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from auction.models import Auction, AuctionRequest, Bid, Category, ChatMessage, Event, Review, User, WorkOrder, WorkSubmission


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


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("auction", "performer", "reviewer", "rating", "created_at")
    list_filter = ("rating",)
    search_fields = ("auction__title", "performer__username", "reviewer__username", "comment")
    readonly_fields = ("auction", "performer", "reviewer", "rating", "comment", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("auction", "sender", "created_at")
    search_fields = ("auction__title", "sender__username", "body")
    list_select_related = ("auction", "sender")
    readonly_fields = ("auction", "sender", "body", "idempotency_key", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

@admin.register(WorkOrder)
class WorkOrderAdmin(admin.ModelAdmin):
    list_display = ("auction", "status", "started_at", "accepted_at")
    list_filter = ("status",)
    search_fields = ("auction__title",)
    readonly_fields = ("auction", "status", "started_at", "updated_at", "accepted_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WorkSubmission)
class WorkSubmissionAdmin(admin.ModelAdmin):
    list_display = ("order", "revision_number", "review_status", "created_at")
    list_filter = ("review_status",)
    readonly_fields = (
        "order", "revision_number", "idempotency_key", "result_text",
        "created_at", "review_status", "feedback", "reviewed_at",
    )

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
