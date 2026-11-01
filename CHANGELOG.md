# Журнал изменений

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
проект придерживается [семантического версионирования](https://semver.org/lang/ru/).

## [Unreleased]

### Добавлено
- Руководство по стилю `docs/STYLE_GUIDE.md`.
- Настройки форматирования: `.editorconfig`, `pyproject.toml` (Black, Ruff),
  `frontend/.prettierrc.json`.
- Шаблон pull request с чек-листом ревью и конфигурация Dependabot.
- `requirements-dev.txt` с инструментами разработки.

### Изменено
- Версии Python-зависимостей ограничены сверху.
- Форматирование суммы в рублях вынесено в `frontend/src/utils/format.ts`.
- Статусы аукциона в `auction/services.py` берутся из `Auction.Status`.

### Удалено
- Неиспользуемая зависимость `@tanstack/react-query`.
- Файл `db.sqlite3` из репозитория.

## [0.1.0] - 2026-10-31

### Добавлено
- Серверная часть: аукционы, модерация, ставки, закрытие торгов.
- Клиентская часть на React + Ant Design.
