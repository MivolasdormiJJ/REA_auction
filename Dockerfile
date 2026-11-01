# ПРОБЛЕМА: Django runserver не подходит для публикации; React должен работать с API на одном домене.
# РЕШЕНИЕ: многоступенчатая сборка React, затем Gunicorn + WhiteNoise в production.
FROM node:22-alpine AS frontend
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend /frontend/dist /app/frontend/dist
RUN python manage.py collectstatic --noinput
RUN useradd --create-home --uid 10001 appuser && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
# ПРОБЛЕМА: миграции без pre-deploy hook не применятся при первом запуске.
# РЕШЕНИЕ: мигрируем перед Gunicorn, но только после успешного подключения к PostgreSQL.
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py bootstrap_user && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000} --workers 2 --timeout 60 --access-logfile - --error-logfile -"]
