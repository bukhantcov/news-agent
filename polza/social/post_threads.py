"""
Публикация следующего поста из очереди polza/social/posts в Threads
(@polza_digital_assistant) через сохранённую Playwright-сессию.

Один .txt в очереди — один пост. Один .json со списком строк — цепочка
(первый пост + "Дополнить ветку" на каждый следующий).

Гоняется ТОЛЬКО локально (не из GitHub Actions — датацентровый IP Meta
блокирует такую автоматизацию мгновенно, отсюда и Playwright-логин руками
вместо API).

    python -m polza.social.login_threads     # один раз, вручную
    python -m polza.social.post_threads --check
    python -m polza.social.post_threads
"""

import asyncio
import json
import sys
from pathlib import Path

from polza.social.common import SESSION_DIR, PostSession

BASE_DIR = Path(__file__).parent
POSTS_DIR = BASE_DIR / "posts"
PUBLISHED_FILE = BASE_DIR / "published.json"
SESSION_PATH = SESSION_DIR / "threads_state.json"
URL = "https://www.threads.com/"


def load_published() -> list[str]:
    if not PUBLISHED_FILE.exists():
        return []
    return json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))


def load_queue_item(path: Path) -> list[str]:
    if path.suffix == ".json":
        return json.loads(path.read_text(encoding="utf-8"))
    return [path.read_text(encoding="utf-8").strip()]


async def check(page) -> int:
    await page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
    await page.wait_for_timeout(3000)
    profile_link = page.locator('a[href="/@polza_digital_assistant"]')
    logged_in = await profile_link.count() > 0
    print(f"Сессия рабочая: {logged_in}")
    return 0 if logged_in else 1


async def publish(page, texts: list[str]) -> bool:
    for label in ("Не сейчас", "Not Now"):
        btn = page.get_by_text(label, exact=True)
        if await btn.count():
            await btn.first.click()
            await page.wait_for_timeout(1000)
            break

    compose_btn = page.locator('svg[aria-label="Создать"]:visible').first
    if not await compose_btn.count():
        print("Не нашёл иконку 'Создать' — сессия могла протухнуть, перезайдите через login_threads.py")
        return False

    await compose_btn.click()
    await page.wait_for_timeout(2000)

    dialog = page.locator('div[role="dialog"]')
    scope = dialog if await dialog.count() else page

    for i, post_text in enumerate(texts):
        if i == 0:
            editor = scope.locator('div[role="textbox"]').first
            if not await editor.count():
                print("Не нашёл редактор поста")
                return False
        else:
            add_row = scope.get_by_text("Дополнить ветку", exact=True)
            if not await add_row.count():
                print(f"Не нашёл 'Дополнить ветку' на посте {i + 1} — цепочка оборвана, публикую то, что успело ввестись")
                break
            await add_row.first.click()
            await page.wait_for_timeout(1000)
            editor = scope.locator('div[role="textbox"]').last

        await editor.click()
        await page.keyboard.type(post_text)
        await page.wait_for_timeout(800)

    publish_btn = scope.get_by_text("Опубликовать", exact=True)
    if not await publish_btn.count():
        print("Кнопка 'Опубликовать' не найдена — публикация не выполнена")
        return False

    await publish_btn.first.click()
    await page.wait_for_timeout(5000)
    return True


async def main() -> int:
    if not SESSION_PATH.exists():
        print(f"Нет сессии {SESSION_PATH}. Сначала: python -m polza.social.login_threads")
        return 1

    async with PostSession(SESSION_PATH, headless=False) as session:
        page = session.page

        if "--check" in sys.argv:
            return await check(page)

        published = load_published()
        queue = [p for p in sorted(POSTS_DIR.glob("*")) if p.suffix in (".txt", ".json") and p.name not in published]
        if not queue:
            print("Очередь пуста")
            return 0

        item = queue[0]
        texts = load_queue_item(item)

        await page.goto(URL, wait_until="domcontentloaded", timeout=30_000)
        await page.wait_for_timeout(3000)

        ok = await publish(page, texts)
        if not ok:
            return 1

        PUBLISHED_FILE.write_text(
            json.dumps(published + [item.name], ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"Опубликовано {item.name}, осталось в очереди: {len(queue) - 1}")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
