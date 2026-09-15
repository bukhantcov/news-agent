# AI News Agent

Автоматический сбор и публикация новостей об искусственном интеллекте.

## Как это работает

- Каждый час агент ищет свежие новости через GigaChat API
- Отбирает только значимые события (релизы, анонсы, обновления)
- Публикует в Telegram канал @DenisBukhancov_CRM_AI

## Запуск на GitHub Actions

1. Форкните репозиторий
2. Добавьте секреты:
   - `BOT_TOKEN` - токен Telegram бота
   - `BASIC_AUTH_KEY` - ключ GigaChat API
3. Actions будут запускаться автоматически каждый час

## Uklad channel poster

`uklad/poster.py` publishes pre-written posts from `uklad/posts/*.html` (Telegram HTML, sorted by filename) one per run. Published filenames are tracked in `uklad/published.json`, which the workflow commits back. Files with `-pin` in the name are pinned after sending.

- Workflow: `.github/workflows/uklad_poster.yml` — Mon/Wed/Fri 10:00 MSK, or run manually
- Secret `BOT_TOKEN` (shared with the news agent), repository variable `UKLAD_CHANNEL_ID` (e.g. `@uklad_app`)
- The bot must be an admin of the channel with post and edit rights
- To add content: drop `NNN-slug.html` into `uklad/posts/` and push
