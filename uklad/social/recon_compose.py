"""
Разведка модалки создания поста/рилса — кликает по композеру и смотрит,
что появилось. Публикует только с флагом --publish.

    python -m uklad.social.recon_compose instagram
    python -m uklad.social.recon_compose instagram <video.mp4> [caption] [--publish]
    python -m uklad.social.recon_compose threads "текст поста" [--publish]
"""

import asyncio
import json
import sys
from pathlib import Path

from uklad.social.common import SESSION_DIR, PostSession

OUT_DIR = Path(__file__).resolve().parent / "session" / "recon"

URLS = {
    "instagram": "https://www.instagram.com/",
    "threads": "https://www.threads.com/",
}

# aria-label кнопки создания поста у каждой площадки (по-русски, раз аккаунт в ru-RU)
COMPOSE_ARIA = {
    "instagram": "Новая публикация",
    "threads": "Создать",
}


async def dump(page, tag: str):
    shot_path = OUT_DIR / f"{tag}.png"
    try:
        await page.screenshot(path=str(shot_path), timeout=8000)
        print(f"Скриншот: {shot_path}")
    except Exception as e:
        print(f"Скриншот не удался: {e}")

    interactive = await page.evaluate("""
        () => Array.from(document.querySelectorAll(
            'button, a[role="link"], [role="button"], svg[aria-label], input, textarea, div[role="textbox"], input[type="file"]'
        )).slice(0, 50).map(el => ({
            tag: el.tagName,
            type: el.getAttribute('type'),
            role: el.getAttribute('role'),
            aria: el.getAttribute('aria-label'),
            placeholder: el.getAttribute('placeholder'),
            text: (el.innerText || '').trim().slice(0, 40),
        }))
    """)
    for el in interactive:
        print(el)


async def run_threads(page) -> int:
    # Аргумент — либо текст одного поста, либо путь к .json со списком постов
    # цепочки (публикуются как единая ветка через "Дополнить ветку").
    arg = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "--publish" else "Тестовая публикация Уклад"
    if arg.endswith(".json"):
        posts = json.loads(Path(arg).read_text(encoding="utf-8"))
    else:
        posts = [arg]

    # DOM держит скрытый дубль инлайн-композера ("Что нового?", rect 0x0) —
    # реальная кнопка открытия редактора это nav-иконка "Создать" внизу экрана.
    compose_btn = page.locator('svg[aria-label="Создать"]:visible').first
    if not await compose_btn.count():
        print("Не нашёл видимую иконку 'Создать' — смотри скриншот before")
        return 1

    await compose_btn.click()
    await page.wait_for_timeout(2000)
    print("--- после клика по инлайн-полю ---")
    await dump(page, "threads_after")

    dialog = page.locator('div[role="dialog"]')
    scope = dialog if await dialog.count() else page

    for i, post_text in enumerate(posts):
        if i == 0:
            editor = scope.locator('div[role="textbox"]').first
            if not await editor.count():
                print("Не нашёл редактор поста — смотри скриншот after")
                return 1
        else:
            add_row = scope.get_by_text("Дополнить ветку", exact=True)
            if not await add_row.count():
                print(f"Не нашёл 'Дополнить ветку' на посте {i + 1} — цепочка оборвана")
                break
            await add_row.first.click()
            await page.wait_for_timeout(1000)
            editor = scope.locator('div[role="textbox"]').last

        await editor.click()
        await page.keyboard.type(post_text)
        await page.wait_for_timeout(800)
        print(f"--- пост {i + 1}/{len(posts)} введён ---")
        await dump(page, f"threads_chain_{i + 1}")

    if "--publish" not in sys.argv:
        print("--publish не передан — на 'Опубликовать' не жму")
        return 0

    publish_btn = scope.get_by_text("Опубликовать", exact=True)
    if not await publish_btn.count():
        print("Кнопка 'Опубликовать' не найдена — публикация не выполнена")
        return 1

    await publish_btn.first.click()
    for wait_step in range(4):
        await page.wait_for_timeout(5000)
        print(f"--- после клика 'Опубликовать', +{(wait_step + 1) * 5}с ---")
        await dump(page, f"threads_after_publish_{wait_step + 1}")
        body_text = await page.evaluate("document.body.innerText")
        print("BODY_SNIPPET:", body_text[:300].replace("\n", " | "))

    return 0


async def main(platform: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session_path = SESSION_DIR / f"{platform}_state.json"

    async with PostSession(session_path, headless=False) as session:
        page = session.page
        await page.goto(URLS[platform], wait_until="domcontentloaded", timeout=30_000)
        await page.add_style_tag(content="""
            *, *::before, *::after {
                transition: none !important;
                animation: none !important;
            }
        """)
        await page.wait_for_timeout(3000)

        # Закрыть диалог "Включить уведомления", если всплыл
        for label in ("Не сейчас", "Not Now"):
            btn = page.get_by_text(label, exact=True)
            if await btn.count():
                await btn.first.click()
                await page.wait_for_timeout(1000)
                break

        print("--- до клика по композеру ---")
        await dump(page, f"{platform}_before")

        if platform == "threads":
            return await run_threads(page)

        aria = COMPOSE_ARIA[platform]
        compose = page.locator(f'svg[aria-label="{aria}"]').first
        if await compose.count() == 0:
            print(f"Не нашёл svg[aria-label='{aria}'] — смотри скриншот before")
            return 1

        await compose.click()
        await page.wait_for_timeout(2500)

        print("--- после клика по композеру ---")
        await dump(page, f"{platform}_after")

        if platform == "instagram":
            # has_text ловит и чужую иконку с пустым видимым текстом (совпадение
            # где-то во вложенном атрибуте) — берём ссылку через точный текстовый узел.
            post_option = page.get_by_text("Публикация", exact=True).locator("xpath=ancestor::a[1]")
            count = await post_option.count()
            print(f"Найдено 'Публикация' (по exact innerText): {count}")
            if count:
                await post_option.click()
                await page.wait_for_timeout(2000)
                print("--- после клика 'Публикация' ---")
                await dump(page, f"{platform}_after_post")

                file_input = page.locator('input[type="file"]')
                fi_count = await file_input.count()
                print(f"input[type=file] найдено: {fi_count}")
                if fi_count and len(sys.argv) > 2:
                    video_path = sys.argv[2]
                    await file_input.first.set_input_files(video_path)
                    await page.wait_for_timeout(4000)
                    print("--- после загрузки видео ---")
                    await dump(page, f"{platform}_after_upload")

                    ok_btn = page.get_by_text("OK", exact=True)
                    if await ok_btn.count():
                        await ok_btn.first.click()
                        await page.wait_for_timeout(2500)
                        print("--- после закрытия инфо про Reels ---")
                        await dump(page, f"{platform}_after_ok")

                    # Шаги "Обрезать" / "Изменить" — жмём "Далее", пока не появится
                    # поле подписи или пока далее не найдено.
                    for step in range(3):
                        caption_box = page.locator('div[role="textbox"], textarea').first
                        if await caption_box.count():
                            print(f"--- поле подписи найдено (шаг {step}) ---")
                            break
                        next_btn = page.get_by_text("Далее", exact=True)
                        if not await next_btn.count():
                            print(f"--- 'Далее' не найдено (шаг {step}) ---")
                            break
                        await next_btn.first.click()
                        await page.wait_for_timeout(2500)
                        print(f"--- после 'Далее' №{step + 1} ---")
                        await dump(page, f"{platform}_after_next_{step + 1}")

                    caption_arg = sys.argv[3] if len(sys.argv) > 3 and sys.argv[3] != "--publish" else "Тестовая публикация Уклад"
                    caption_box = page.locator('div[role="textbox"], textarea').first
                    if await caption_box.count():
                        await caption_box.click()
                        await page.keyboard.type(caption_arg)
                        await page.wait_for_timeout(1000)
                        print("--- после ввода подписи ---")
                        await dump(page, f"{platform}_after_caption")

                    if "--publish" in sys.argv:
                        # get_by_text без scope ловит невидимую иконку "поделиться"
                        # на фоновом посте ленты — ищем только внутри диалога модалки.
                        dialog = page.locator('div[role="dialog"]')
                        share_btn = dialog.get_by_text("Поделиться", exact=True)
                        if await share_btn.count():
                            await share_btn.first.click()
                            for wait_step in range(6):
                                await page.wait_for_timeout(5000)
                                print(f"--- после клика 'Поделиться', +{(wait_step + 1) * 5}с ---")
                                await dump(page, f"{platform}_after_share_{wait_step + 1}")
                                body_text = await page.evaluate("document.body.innerText")
                                print("BODY_SNIPPET:", body_text[:300].replace(chr(10), ' | '))
                        else:
                            print("Кнопка 'Поделиться' не найдена — публикация не выполнена")
                    else:
                        print("--publish не передан — на 'Поделиться' не жму")

    return 0


if __name__ == "__main__":
    platform = sys.argv[1] if len(sys.argv) > 1 else "instagram"
    sys.exit(asyncio.run(main(platform)))
