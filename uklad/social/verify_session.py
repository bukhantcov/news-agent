"""
Проверка живой сессии без единого поста — просто открывает профиль и
смотрит, залогинены мы или нет. Headless, ничего не публикует.

    python -m uklad.social.verify_session instagram
    python -m uklad.social.verify_session threads
"""

import asyncio
import sys

from uklad.social.common import SESSION_DIR, PostSession

URLS = {
    "instagram": "https://www.instagram.com/",
    "threads": "https://www.threads.com/",
}

async def main(platform: str) -> int:
    session_path = SESSION_DIR / f"{platform}_state.json"
    async with PostSession(session_path, headless=True) as session:
        await session.page.goto(URLS[platform], wait_until="domcontentloaded", timeout=30_000)
        await session.page.wait_for_timeout(3000)

        url = session.page.url
        has_login_form = await session.page.locator(
            'input[name="username"], input[autocomplete="username"]'
        ).count()
        title = await session.page.title()
        body_snippet = (await session.page.inner_text("body"))[:300].replace("\n", " ")

        print(f"url после загрузки: {url}")
        print(f"title: {title}")
        print(f"есть форма логина: {bool(has_login_form)}")
        print(f"начало body: {body_snippet}")

        if "/accounts/login" in url or has_login_form:
            print(f"{platform}: НЕ залогинены")
            return 1

        print(f"{platform}: похоже залогинены")
        return 0


if __name__ == "__main__":
    platform = sys.argv[1] if len(sys.argv) > 1 else "instagram"
    if platform not in URLS:
        print(f"platform должен быть один из {list(URLS)}")
        sys.exit(1)
    sys.exit(asyncio.run(main(platform)))
