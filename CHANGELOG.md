# Changelog

Все заметные изменения проекта. Формат — [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/),
версионирование — [SemVer](https://semver.org/lang/ru/) (см. docs/STYLE_GUIDE.md, раздел 4).

## [Unreleased]

### Добавлено
- Руководство по стилю команды (`docs/STYLE_GUIDE.md`) и отчёт code review (`docs/CODE_REVIEW.md`).
- Конфигурации форматирования: `.editorconfig`, `pyproject.toml` (ruff), `frontend/.prettierrc.json`.
- Шаблон pull request с чек-листом review, настройка Dependabot.

### Исправлено
- Удалены неиспользуемые и повторные импорты в `auction/views.py`.

## [1.0.0] — публикация приложения

### Добавлено
- Платформа обратных аукционов: регистрация, каталог, модерация, открытые ставки,
  определение победителя по второй цене, уведомления, административная панель.
