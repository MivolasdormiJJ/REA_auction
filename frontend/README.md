# REA Auction — клиентское приложение

Ветка разработки: `dev_any`. Интерфейс на **React 19, TypeScript, Vite, Ant Design**.

## Основные команды

```bash
npm ci
npm run dev
npm run build
npm run lint
```

Для разработки Django запускается отдельно на `http://localhost:8000`, а Vite проксирует запросы `/api` через `frontend/vite.config.ts`. В production React собирается командой `npm run build`; файлы из `dist/` раздаёт Django/WhiteNoise в общем Docker-контейнере на Render.

## Страницы

- `/design-preview`: публичная учебная демонстрация без создания реальных ставок;
- `/login`, `/register`: вход и регистрация с email, **без подтверждения почты**;
- `/auctions`, `/auctions/:id`: каталог, открытые ставки, результаты;
- `/auctions/new`, `/cabinet`: создание задач и кабинет заказчика;
- `/notifications`, `/profile`: результаты торгов и профиль;
- `/moderation`, `/admin`: интерфейсы с проверкой прав на сервере.

## Организация

- `src/pages/` — отдельные страницы React;
- `src/components/` — общие компоненты и логотип;
- `src/api/` — типы и Axios-клиент для Django REST API;
- `src/context/` — состояние сессии пользователя;
- `src/app-theme.css` — оформление приложения;
- `src/pages/DesignPreviewPage.css` — стили публичного макета;
- `src/App.tsx` — маршруты и защита страниц по ролям.

## Развёртывание

- Реальное приложение: https://rea-auction.onrender.com
- Учебный статический макет: https://mivolasdormijj.github.io/REA_auction/

GitHub Pages обслуживает **только статическую сборку** и не поддерживает серверные Django-сессии и ставки. Деплой Render берёт код из `dev_any`. Ветку `main` не изменяем.
