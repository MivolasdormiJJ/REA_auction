"""Настройки Django для приложения аукциона."""

import os
from pathlib import Path

import dj_database_url

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.environ.get("DEBUG", "1") == "1"

SECRET_KEY = os.environ.get(
    "SECRET_KEY",
    "local-educational-demo-only-change-me",
)

if not DEBUG and SECRET_KEY == "local-educational-demo-only-change-me":
    raise RuntimeError("Set SECRET_KEY")

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "localhost,127.0.0.1,testserver",
).split(",")
# ПРОБЛЕМА: динамический домен Railway нельзя предугадать.
# РЕШЕНИЕ: разрешаем выданный домен, а не любой host.
railway_domain = os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip()
if railway_domain:
    ALLOWED_HOSTS.append(railway_domain)

# Фронтенд на Vite (порт 5173) проксирует /api, Origin браузера остаётся его
CSRF_TRUSTED_ORIGINS = os.environ.get(
    "CSRF_TRUSTED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")
if railway_domain:
    CSRF_TRUSTED_ORIGINS.append("https://" + railway_domain)

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "django.contrib.sessions",
    "rest_framework",
    "auction",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
]

ROOT_URLCONF = "config.urls"

AUTH_USER_MODEL = "auction.User"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
        "OPTIONS": {
            "transaction_mode": "IMMEDIATE",
            "timeout": 20,
        },
    },
}

# ПРОБЛЕМА: Railway выдаёт PostgreSQL-подключение через DATABASE_URL.
# РЕШЕНИЕ: поддерживаем URL без поломки локальной POSTGRES_HOST-конфигурации.
if os.environ.get("DATABASE_URL"):
    DATABASES = {"default": dj_database_url.config(conn_max_age=600, conn_health_checks=True)}
elif os.environ.get("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "HOST": os.environ["POSTGRES_HOST"],
            "PORT": os.environ.get("POSTGRES_PORT", "5432"),
            "NAME": os.environ.get("POSTGRES_DB", "auction"),
            "USER": os.environ.get("POSTGRES_USER", "auction"),
            "PASSWORD": os.environ["POSTGRES_PASSWORD"],
        },
    }

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": ("rest_framework.pagination.PageNumberPagination"),
    "PAGE_SIZE": 20,
}

USE_TZ = True
TIME_ZONE = "UTC"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = not DEBUG
# ПРОБЛЕМА: Django за управляемым HTTPS-прокси может ошибочно считать запрос HTTP.
# РЕШЕНИЕ: использовать X-Forwarded-Proto только при явно включённой настройке.
if os.environ.get("TRUST_PROXY_HTTPS") == "1":
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CSRF_COOKIE_SECURE = not DEBUG

# ПРОБЛЕМА: без production-политик браузер может получить менее защищённые ответы.
# РЕШЕНИЕ: включаем дополнительные ограничения при DEBUG=False.
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_HSTS_SECONDS = 31536000 if not DEBUG else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = not DEBUG
SECURE_REFERRER_POLICY = 'same-origin'
X_FRAME_OPTIONS = 'DENY'


TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
]

STATIC_URL = "/static/"
# ПРОБЛЕМА: GitHub Pages не может обслуживать защищённые Django-сессии.
# РЕШЕНИЕ: в production React и Django API работают с одного HTTPS-домена.
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
if FRONTEND_DIST_DIR.is_dir():
    WHITENOISE_ROOT = FRONTEND_DIST_DIR
STATIC_ROOT = BASE_DIR / "staticfiles"
# Редирект включается только при наличии правильно настроенного HTTPS proxy.
SECURE_SSL_REDIRECT = not DEBUG and os.environ.get("SECURE_SSL_REDIRECT") == "1"
