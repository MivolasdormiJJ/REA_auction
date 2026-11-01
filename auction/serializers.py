from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.contrib.auth.validators import UnicodeUsernameValidator
from django.db.models.functions import Lower
from rest_framework import serializers
from .models import Auction, Bid, Category, User


class AuctionSerializer(serializers.ModelSerializer):
    owner_id = serializers.IntegerField(read_only=True)
    winner_id = serializers.SerializerMethodField()
    payment_kopecks = serializers.SerializerMethodField()

    class Meta:
        model = Auction
        fields = [
            "id",
            "owner_id",
            "category",
            "title",
            "description",
            "budget_kopecks",
            "ends_at",
            "due_at",
            "status",
            "moderation_reason",
            "winner_id",
            "payment_kopecks",
            "closed_at",
        ]
        read_only_fields = ["status", "moderation_reason", "closed_at"]
        extra_kwargs = {
            "title": {"min_length": 5},
            "description": {"min_length": 20, "max_length": 5000},
            "budget_kopecks": {"min_value": 100, "max_value": 10**12},
        }

    def get_winner_id(self, obj):
        return obj.winner_id if obj.status == "closed" else None

    def get_payment_kopecks(self, obj):
        return obj.payment_kopecks if obj.status == "closed" else None

    def validate(self, attrs):
        end = attrs.get("ends_at", getattr(self.instance, "ends_at", None))
        due = attrs.get("due_at", getattr(self.instance, "due_at", None))
        if end <= timezone.now() or due <= end:
            raise serializers.ValidationError(
                "Окончание торгов должно быть в будущем, срок работы — позже торгов"
            )
        return attrs


class BidInput(serializers.Serializer):
    amount_kopecks = serializers.IntegerField(min_value=1, max_value=10**12)


class BidSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bid
        fields = ["id", "auction_id", "amount_kopecks", "created_at"]


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name"]


class DecisionInput(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, allow_blank=False)


class RegistrationInput(serializers.Serializer):
    username = serializers.CharField(min_length=3, max_length=150, trim_whitespace=True)
    email = serializers.EmailField(max_length=254)
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=128)

    def validate_username(self, value):
        # ПРОБЛЕМА: формы без серверной валидации допускали некорректные имена.
        # РЕШЕНИЕ: применяем валидатор Django и проверяем уникальность без учёта регистра.
        try:
            UnicodeUsernameValidator()(value)
        except DjangoValidationError as error:
            raise serializers.ValidationError(error.messages) from error
        if User.objects.annotate(lower_name=Lower("username")).filter(lower_name=value.lower()).exists():
            raise serializers.ValidationError("Это имя уже занято")
        return value

    def validate_email(self, value):
        email = value.lower()
        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Этот email уже используется")
        return email

    def validate(self, attrs):
        password = attrs["password"]
        if len(password) < 12:
            raise serializers.ValidationError({"password": "Используйте минимум 12 символов"})
        user = User(username=attrs["username"], email=attrs["email"])
        try:
            validate_password(password, user=user)
        except DjangoValidationError as error:
            raise serializers.ValidationError({"password": error.messages}) from error
        return attrs
