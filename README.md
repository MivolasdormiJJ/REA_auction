# REA Auction — платформа обратных аукционов

Учебный полнофункциональный веб-проект для публикации студенческих задач и выбора исполнителя через открытые обратные аукционы по правилу второй цены.

- **Сайт с Django API:** https://rea-auction.onrender.com/
- **Статическая учебная демонстрация:** https://mivolasdormijj.github.io/REA_auction/
- **Рабочая ветка:** `dev_any` — не выполняйте слияние в `main`.

## Технологии

Backend: Python 3.12, Django 5.2, Django REST Framework, PostgreSQL, Gunicorn, WhiteNoise. Frontend: React, TypeScript, Vite, Ant Design, Axios. Развёртывание: Docker и Render; CI — GitHub Actions. Статическая учебная страница дополнительно публикуется через GitHub Pages.

## Возможности

Регистрация без подтверждения email, вход через Django sessions/CSRF, каталог с 24 категориями по направлениям подготовки, создание задач и модерация, открытые ставки, выбор победителя и цены по правилу второго минимума, уведомления о результатах, административная панель и примеры учебных аукционов.

## Запуск и тесты

```bash
# Установить Python-зависимости и подготовить базу
pip install -r requirements.txt
python manage.py migrate
python manage.py test auction

# Разработка интерфейса
cd frontend
npm ci
npm run dev
npm run build
```

Для локального запуска с PostgreSQL предусмотрен `compose.yaml` и шаблон `.env.example`. Vite проксирует `/api` на `http://localhost:8000`. В production многоступенчатый `Dockerfile` собирает React, затем запускает Django через Gunicorn; PostgreSQL подключается через `DATABASE_URL`.

Команда `python manage.py close_auctions --loop` закрывает просроченные торги и определяет результат. Изменения в `dev_any` автоматически проверяются GitHub Actions и публикуются Render.

## Документация

- [Контракт API](docs/API.md)
- [Архитектура фронтенда](docs/frontend.md)
- [Регистрация](docs/registration.md)
- [Демонстрация работы аукциона](docs/design-preview.md)

Система предназначена для учебной демонстрации. Настоящие платежи, подтверждение email и восстановление пароля пока не реализованы.
