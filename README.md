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

## Polza channel posters (Telegram)

Two independent FIFO queues, both posting to `@Polza_digital_CRM`, both mirrored to Яндекс.Дзен automatically by Telegram's own Дзен integration on that channel:

- `polza/poster.py` — archive queue, posts adapted from already-live blog articles (`polza/posts/*.html`). Workflow `.github/workflows/polza_poster.yml`, daily 10:00 MSK.
- `polza/fresh/poster.py` — synced 1:1 with the blog's own daily publish order (`polza/fresh/posts/*.html`). Workflow `.github/workflows/polza_fresh_poster.yml`, daily 10:05 MSK.

Both reuse the same secret `POLZA_BOT_TOKEN` and repository variable `POLZA_CHANNEL_ID`. Same file conventions as `uklad/poster.py` (`-pin` marker, `published.json` tracker committed back by the workflow).

## Polza Threads poster

`polza/social/post_threads.py` posts to `https://www.threads.com/@polza_digital_assistant` via a Playwright browser session — same approach as `uklad/social`, since there is no official Threads API access here. **Runs locally only, never from GitHub Actions** — Meta blocks datacenter-IP browser automation, and the session cookie is never committed.

Setup (once, on your own machine):

```
pip install -r polza/social/requirements.txt
playwright install chromium
python -m polza.social.login_threads   # visible window, log in by hand
```

Then, whenever you want to post:

```
python -m polza.social.post_threads --check   # confirm the session still works
python -m polza.social.post_threads            # posts the next queued item
```

Queue: `polza/social/posts/` — a `.txt` file is a single post, a `.json` file is a list of strings posted as a thread (first post + "Дополнить ветку" for each next line). Published filenames tracked in `polza/social/published.json`. Content here is written in the account's own casual first-person voice (the assistant persona is female — feminine verb forms) — do not reuse the Telegram copy verbatim.

Posts 001–003 were actually published by hand through a real logged-in Chrome tab rather than this script — WebKit rendered blank on first try, and the Playwright anti-detection fixes that would've made Chromium reliable here (persistent profile, `--disable-blink-features=AutomationControlled`) were judged too close to bot-detection evasion to ship. `post_threads.py` is still here and correct for whenever that's revisited; `published.json` reflects the true state either way so the queue doesn't duplicate.
