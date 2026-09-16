"""
Автопостинг очереди тезисов в Threads.

Берёт следующий неопубликованный текст из threads_queue.json, публикует его
через сохранённую сессию (uklad/social/session/threads_state.json или секрет
THREADS_SESSION_STATE в CI), отмечает в threads_published.json.

Официального API нет — постинг идёт через тот же браузерный механизм, что и
recon_compose.py (Playwright + сохранённые cookies), но headless и без
пошаговых скриншотов: для CI, не для отладки.

    python -m uklad.social.poster_threads            # публикует
    python -m uklad.social.poster_threads --dry-run   # только проверяет, что нашёл бы

Требует переменную окружения THREADS_SESSION_STATE (не файл, а её содержимое)
в CI, ИЛИ локальный файл session/threads_state.json.
"""

import asyncio
import json
import os
import sys
from pathlib import Path

from uklad.social.common import SESSION_DIR, PostSession

BASE = Path(__file__).resolve().parent
QUEUE_PATH = BASE / "threads_queue.json"
PUBLISHED_PATH = BASE / "threads_published.json"
URL = "https://www.threads.com/"


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_session_file() -> Path:
    """В CI сессии на диске нет — материализуем её из секрета перед запуском."""
    session_path = SESSION_DIR / "threads_state.json"
    if session_path.exists():
        return session_path
    state = os.environ.get("THREADS_SESSION_STATE")
    if not state:
        raise SystemExit(
            "Нет ни session/threads_state.json, ни переменной THREADS_SESSION_STATE"
        )
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(state, encoding="utf-8")
    return session_path


async def publish_one(text: str, dry_run: bool) -> bool:
    session_path = _ensure_session_file()

    async with PostSession(session_path, headless=True) as session:
        page = session.page
        await page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        await page.add_style_tag(content="*{transition:none!important;animation:none!important}")
        await page.wait_for_timeout(3000)

        for label in ("Не сейчас", "Not Now"):
            btn = page.get_by_text(label, exact=True)
            if await btn.count():
                await btn.first.click()
                await page.wait_for_timeout(1000)
                break

        compose_btn = page.locator('svg[aria-label="Создать"]:visible').first
        if not await compose_btn.count():
            print("Не нашёл кнопку 'Создать' — вероятно, сессия истекла или вёрстка сменилась")
            return False
        await compose_btn.click()
        await page.wait_for_timeout(2000)

        dialog = page.locator('div[role="dialog"]')
        scope = dialog if await dialog.count() else page
        editor = scope.locator('div[role="textbox"]').first
        if not await editor.count():
            print("Не нашёл поле ввода поста")
            return False

        await editor.click()
        await page.keyboard.type(text)
        await page.wait_for_timeout(800)

        if dry_run:
            print("dry-run: текст введён, публикацию не подтверждаю")
            return True

        publish_btn = scope.get_by_text("Опубликовать", exact=True)
        if not await publish_btn.count():
            print("Не нашёл кнопку 'Опубликовать'")
            return False
        await publish_btn.first.click()
        await page.wait_for_timeout(6000)
        return True


async def main() -> int:
    dry_run = "--dry-run" in sys.argv

    queue = _load_json(QUEUE_PATH, [])
    published = _load_json(PUBLISHED_PATH, [])

    if len(published) >= len(queue):
        print("Очередь пуста — все тезисы опубликованы")
        return 0

    idx = len(published)
    text = queue[idx]
    print(f"Публикую тезис {idx + 1}/{len(queue)}: {text[:60]}...")

    ok = await publish_one(text, dry_run)
    if not ok:
        print("Публикация не удалась, состояние не меняю")
        return 1

    if not dry_run:
        published.append(idx)
        PUBLISHED_PATH.write_text(
            json.dumps(published, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Опубликовано, отмечено в {PUBLISHED_PATH.name}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
