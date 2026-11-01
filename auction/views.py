import hashlib
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.conf import settings
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.db import IntegrityError
from urllib.parse import urlencode
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from .models import Auction, AuctionRequest, Category, User
from .serializers import (
    AuctionSerializer,
    BidInput,
    BidSerializer,
    CategorySerializer,
    DecisionInput,
    RegistrationInput,
)
from .services import eligible, transition, place_bid, Conflict, event


class LoginRateThrottle(SimpleRateThrottle):
    scope = "login"
    rate = "10/min"

    def get_cache_key(self, request, view):
        # ПРОБЛЕМА: без ограничения попыток можно массово подбирать пароль.
        # РЕШЕНИЕ: лимит попыток входа по IP. В production нужен общий Redis-кеш.
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}



class RegisterRateThrottle(SimpleRateThrottle):
    scope = "register"
    rate = "3/hour"

    def get_cache_key(self, request, view):
        # ПРОБЛЕМА: массовая регистрация и отправка писем создают нагрузку.
        # РЕШЕНИЕ: ограничиваем запросы по IP (в production нужен общий кеш).
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


class VerifyRateThrottle(SimpleRateThrottle):
    scope = "verify"
    rate = "20/hour"

    def get_cache_key(self, request, view):
        return self.cache_format % {"scope": self.scope, "ident": self.get_ident(request)}


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([RegisterRateThrottle])
@csrf_protect
def register(request):
    # ПРОБЛЕМА: пока SMTP не настроен, нельзя создавать аккаунты без возможности
    # подтвердить email. РЕШЕНИЕ: в production регистрация закрыта без SMTP.
    if not settings.DEBUG and not getattr(settings, "REGISTRATION_EMAIL_ENABLED", False):
        return Response({"detail": "Регистрация временно недоступна: почта не настроена"}, status=503)
    serializer = RegistrationInput(data=request.data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    user = User(username=data["username"], email=data["email"], email_verified=False)
    user.set_password(data["password"])
    try:
        # Важно: email должен уйти до фиксации транзакции, чтобы SMTP-ошибка
        # не оставила пользователя, который не может подтвердить адрес.
        with transaction.atomic():
            user.save()
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            url = request.build_absolute_uri("/verify-email?" + urlencode({"uid": uid, "token": token}))
            send_mail(
                "REA Auction — подтверждение email",
                "Здравствуйте! Подтвердите регистрацию, открыв ссылку:\n" + url + "\n\nЕсли вы не регистрировались, проигнорируйте это письмо.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
                fail_silently=False,
            )
    except IntegrityError:
        raise ValidationError({"detail": "Имя пользователя или email уже используются"})
    except Exception as error:
        # Не раскрываем SMTP-пароли/настройки или внутренние детали через API.
        from django.core.mail import BadHeaderError
        from smtplib import SMTPException
        if isinstance(error, (SMTPException, OSError, BadHeaderError)):
            return Response({"detail": "Не удалось отправить письмо подтверждения. Попробуйте позднее."}, status=503)
        raise
    return Response({"detail": "Письмо подтверждения отправлено. Проверьте почту."}, status=201)


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@throttle_classes([VerifyRateThrottle])
@csrf_protect
def verify_email(request):
    uid, token = request.data.get("uid"), request.data.get("token")
    if not isinstance(uid, str) or not isinstance(token, str) or len(uid) > 128 or len(token) > 128:
        raise ValidationError({"detail": "Недействительная ссылка подтверждения"})
    try:
        user_id = urlsafe_base64_decode(uid).decode("utf-8")
        user = User.objects.get(pk=user_id)
    except (ValueError, TypeError, UnicodeError, OverflowError, User.DoesNotExist):
        raise ValidationError({"detail": "Недействительная ссылка подтверждения"})
    if user.email_verified:
        return Response({"detail": "Email уже подтверждён"})
    if not default_token_generator.check_token(user, token):
        raise ValidationError({"detail": "Ссылка недействительна или срок её действия истёк"})
    user.email_verified = True
    user.save(update_fields=["email_verified"])
    return Response({"detail": "Email подтверждён. Теперь можно войти."})


class Admitted(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and request.user.is_active
            and request.user.email_verified
        )


@api_view(["GET"])
@permission_classes([permissions.AllowAny])
def csrf(request):
    return Response({"csrfToken": get_token(request)})


@api_view(["POST"])
@permission_classes([permissions.AllowAny])
@csrf_protect
@throttle_classes([LoginRateThrottle])
def signin(request):
    username, password = request.data.get("username"), request.data.get("password")
    if not isinstance(username, str) or not isinstance(password, str):
        raise ValidationError("Передайте username и password")
    user = authenticate(request, username=username, password=password)
    if not user:
        raise PermissionDenied("Неверные данные или нет доступа")
    eligible(user)
    login(request, user)
    return Response(
        {"id": user.pk, "username": user.username, "can_moderate": user.has_perm("auction.moderate_auction"), "csrfToken": get_token(request)}
    )


@api_view(["POST"])
def signout(request):
    logout(request)
    return Response(status=204)


@api_view(["GET"])
def me(request):
    eligible(request.user)
    return Response(
        {
            "id": request.user.pk,
            "username": request.user.username,
            "can_moderate": request.user.has_perm("auction.moderate_auction"),
        }
    )


class CategoryViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [Admitted]
    queryset = Category.objects.order_by("id")
    serializer_class = CategorySerializer


class AuctionViewSet(viewsets.ModelViewSet):
    permission_classes = [Admitted]
    serializer_class = AuctionSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        u = self.request.user
        visible = Q(owner=u) | Q(status__in=["open", "closed"])
        if u.has_perm("auction.moderate_auction"):
            visible |= Q(status="review")
        qs = Auction.objects.filter(visible).order_by("-id")
        if self.action == "list":
            for param in ["status", "category"]:
                value = self.request.query_params.get(param)
                if value:
                    if param == "category" and not value.isdecimal():
                        raise ValidationError(
                            {"category": "Требуется числовой идентификатор"}
                        )
                    qs = qs.filter(**{param: value})
            if self.request.query_params.get("mine") == "1":
                qs = qs.filter(owner=u)
            if self.request.query_params.get("search"):
                qs = qs.filter(
                    Q(title__icontains=self.request.query_params["search"])
                    | Q(description__icontains=self.request.query_params["search"])
                )
        return qs

    def create(self, request, *args, **kwargs):
        key = request.headers.get("Idempotency-Key", "")
        if not key.strip() or len(key) > 80:
            raise ValidationError({"Idempotency-Key": "Укажите ключ длиной до 80 символов"})
        fingerprint = hashlib.sha256(
            json.dumps(request.data, sort_keys=True, ensure_ascii=False,
                       separators=(",", ":"), default=str).encode("utf-8")
        ).hexdigest()
        # ПРОБЛЕМА: два параллельных POST с одним ключом могли создать два заказа.
        # РЕШЕНИЕ: блокируем строку заказчика и сохраняем заказ и ключ в одной транзакции.
        # Уникальное ограничение в БД защищает от нарушения инварианта.
        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            prior = AuctionRequest.objects.filter(owner=request.user, idempotency_key=key).first()
            if prior:
                if prior.payload_hash != fingerprint:
                    raise Conflict("Ключ уже использован для другого заказа")
                return Response(self.get_serializer(prior.auction).data, status=200)
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            auction = serializer.save(owner=request.user)
            event(auction, request.user, "created")
            AuctionRequest.objects.create(
                owner=request.user, idempotency_key=key,
                payload_hash=fingerprint, auction=auction,
            )
            return Response(self.get_serializer(auction).data, status=201)

    def partial_update(self, request, *args, **kwargs):
        # Блокировка та же, что при публикации: нельзя изменить условия
        # между проверкой черновика и записью опубликованного аукциона.
        with transaction.atomic():
            a = get_object_or_404(
                self.get_queryset().select_for_update(), pk=kwargs["pk"]
            )
            if a.owner_id != request.user.pk:
                raise PermissionDenied()
            if a.status not in ("draft", "rejected"):
                raise Conflict("Условия заморожены после отправки на модерацию")
            s = self.get_serializer(a, data=request.data, partial=True)
            s.is_valid(raise_exception=True)
            s.save()
            event(a, request.user, "edited")
            return Response(s.data)

    def do_transition(self, request, action):
        a = self.get_object()
        reason = ""
        if action != "submit":
            s = DecisionInput(data=request.data)
            s.is_valid(raise_exception=True)
            reason = s.validated_data["reason"]
        result = transition(a.pk, request.user, action, reason)
        return Response(self.get_serializer(result).data)

    @action(detail=True, methods=["post"])
    def submit(self, request, pk=None):
        return self.do_transition(request, "submit")

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        return self.do_transition(request, "approve")

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        return self.do_transition(request, "reject")

    @action(detail=True, methods=["get", "post"])
    def bids(self, request, pk=None):
        a = self.get_object()
        if request.method == "GET":
            # Даже заказчик и модератор получают исключительно свои ставки.
            return Response(
                BidSerializer(a.bids.filter(bidder=request.user), many=True).data
            )
        s = BidInput(data=request.data)
        s.is_valid(raise_exception=True)
        key = request.headers.get("Idempotency-Key", "")
        if not key.strip() or len(key) > 80:
            raise ValidationError(
                {"Idempotency-Key": "Укажите непустой ключ длиной до 80 символов"}
            )
        bid, created = place_bid(
            a.pk, request.user, s.validated_data["amount_kopecks"], key
        )
        return Response(BidSerializer(bid).data, status=201 if created else 200)
