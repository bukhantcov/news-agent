"""
Автопостинг очереди карточек в Instagram.

Берёт следующий неопубликованный пункт из instagram_queue.json, рендерит
карточку шаблоном (templates/render_card.py), публикует через сохранённую
сессию (session/instagram_state.json или секрет INSTAGRAM_SESSION_STATE),
отмечает в instagram_published.json.

Механика клика — та же цепочка, что recon_compose.py нащупал вручную для
одиночного изображения: "Новая публикация" -> "Публикация" -> upload ->
(до 3 раз "Далее") -> подпись -> "Поделиться". Headless, без скриншотов
на каждый шаг — для CI, не для отладки.

    python3 -m uklad.social.poster_instagram            # публикует
    python3 -m uklad.social.poster_instagram --dry-run   # до "Поделиться" не доходит
"""

import asyncio
import base64
import json
import os
import subprocess
import sys
from pathlib import Path

from uklad.social.common import SESSION_DIR, PostSession

BASE = Path(__file__).resolve().parent
QUEUE_PATH = BASE / "instagram_queue.json"
PUBLISHED_PATH = BASE / "instagram_published.json"
TEMPLATES_DIR = BASE / "templates"
EXPORTS_DIR = TEMPLATES_DIR / "exports"
DEBUG_DIR = BASE / "session" / "recon"
URL = "https://www.instagram.com/"


def _load_json(path: Path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def _ensure_session_file() -> Path:
    session_path = SESSION_DIR / "instagram_state.json"
    if session_path.exists():
        return session_path
    state = os.environ.get("INSTAGRAM_SESSION_STATE")
    if not state:
        raise SystemExit(
            "Нет ни session/instagram_state.json, ни переменной INSTAGRAM_SESSION_STATE"
        )
    session_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        raw = base64.b64decode(state).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        raw = state
    session_path.write_text(raw, encoding="utf-8")
    return session_path


def render_image(entry: dict) -> Path:
    out_path = EXPORTS_DIR / f"{entry['post']}.png"
    if out_path.exists():
        return out_path
    args = ["python3", str(TEMPLATES_DIR / "render_card.py"), entry["template"], "-o", str(out_path)]
    for key, value in entry["fields"].items():
        args += [f"--{key}", value]
    subprocess.run(args, check=True, cwd=TEMPLATES_DIR)
    return out_path


async def _dump_debug(page) -> None:
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    shot = DEBUG_DIR / "instagram_poster_failure.png"
    try:
        await page.screenshot(path=str(shot), timeout=8000)
        print(f"Скриншот отказа: {shot}")
    except Exception as e:
        print(f"Скриншот не удался: {e}")
    try:
        body_text = await page.evaluate("document.body.innerText")
        print("BODY_SNIPPET:", body_text[:500].replace("\n", " | "))
    except Exception as e:
        print(f"Не удалось прочитать текст страницы: {e}")


async def publish_one(image_path: Path, caption: str, dry_run: bool) -> bool:
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

        compose = page.locator('svg[aria-label="Новая публикация"]').first
        if not await compose.count():
            print("Не нашёл 'Новая публикация'")
            await _dump_debug(page)
            return False
        await compose.click()
        await page.wait_for_timeout(2000)

        post_option = page.get_by_text("Публикация", exact=True).locator("xpath=ancestor::a[1]")
        if not await post_option.count():
            print("Не нашёл пункт меню 'Публикация'")
            await _dump_debug(page)
            return False
        await post_option.click()
        await page.wait_for_timeout(2000)

        file_input = page.locator('input[type="file"]')
        if not await file_input.count():
            print("Не нашёл input[type=file]")
            await _dump_debug(page)
            return False
        await file_input.first.set_input_files(str(image_path))
        await page.wait_for_timeout(4000)

        for _ in range(3):
            caption_box = page.locator('div[role="textbox"], textarea').first
            if await caption_box.count():
                break
            next_btn = page.get_by_text("Далее", exact=True)
            if not await next_btn.count():
                break
            await next_btn.first.click()
            await page.wait_for_timeout(2500)

        caption_box = page.locator('div[role="textbox"], textarea').first
        if not await caption_box.count():
            print("Не нашёл поле подписи")
            await _dump_debug(page)
            return False
        await caption_box.click()
        await page.keyboard.type(caption)
        await page.wait_for_timeout(1000)

        if dry_run:
            print("dry-run: карточка загружена, подпись введена, публикацию не подтверждаю")
            return True

        dialog = page.locator('div[role="dialog"]')
        share_btn = dialog.get_by_text("Поделиться", exact=True)
        if not await share_btn.count():
            print("Не нашёл кнопку 'Поделиться'")
            await _dump_debug(page)
            return False
        await share_btn.first.click()
        await page.wait_for_timeout(8000)
        return True


async def main() -> int:
    dry_run = "--dry-run" in sys.argv

    queue = _load_json(QUEUE_PATH, [])
    published = _load_json(PUBLISHED_PATH, [])
    published_posts = {p for p in published}

    remaining = [e for e in queue if e["post"] not in published_posts]
    if not remaining:
        print("Очередь пуста — все карточки опубликованы")
        return 0

    entry = remaining[0]
    print(f"Публикую {entry['post']} ({len(queue) - len(published)} осталось)")

    image_path = render_image(entry)
    ok = await publish_one(image_path, entry["caption"], dry_run)
    if not ok:
        print("Публикация не удалась, состояние не меняю")
        return 1

    if not dry_run:
        published.append(entry["post"])
        PUBLISHED_PATH.write_text(
            json.dumps(published, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Опубликовано, отмечено в {PUBLISHED_PATH.name}")

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
