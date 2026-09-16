"""
Транспорт для постинга в Threads через Playwright — копия uklad/social/common.py.

Официального API нет (нет Meta-токена), поэтому браузер под тем же аккаунтом,
которым владелец пользуется руками. Вход — только вручную (см. login_threads.py):
пароль этот код не видит и не хранит, сохраняется только storage_state сессии
(cookies), локально, вне git.
"""

import logging
from pathlib import Path

from playwright.async_api import async_playwright, Page

logger = logging.getLogger("polza_social")

SESSION_DIR = Path(__file__).resolve().parent / "session"


async def login_and_save_session(login_url: str, session_path: Path, timeout_ms: int = 300_000) -> bool:
    """Видимое окно, вход вручную, сохранение storage_state по cookie sessionid."""
    session_path.parent.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=False)
        try:
            context = await browser.new_context(locale="ru-RU")
            page = await context.new_page()
            await page.goto(login_url, timeout=60_000)
            logger.info("Окно открыто — войдите в аккаунт вручную")

            waited = 0
            while waited < timeout_ms:
                if any(c["name"] == "sessionid" for c in await context.cookies()):
                    await page.wait_for_timeout(2000)
                    await context.storage_state(path=str(session_path))
                    logger.info("Сессия сохранена: %s", session_path)
                    return True
                await page.wait_for_timeout(2000)
                waited += 2000

            logger.warning("Вход не обнаружен за %d с — сессия не сохранена", timeout_ms // 1000)
            return False
        finally:
            await browser.close()


class PostSession:
    """Один браузер с сохранённой сессией — на весь запуск, не на пост."""

    def __init__(self, session_path: Path, headless: bool = True):
        if not session_path.exists():
            raise FileNotFoundError(
                f"Нет сессии {session_path}. Сначала запустите login_threads.py"
            )
        self.session_path = session_path
        self.headless = headless
        self._pw = None
        self._browser = None
        self.page: Page | None = None

    async def __aenter__(self) -> "PostSession":
        self._pw = await async_playwright().start()
        self._browser = await self._pw.chromium.launch(headless=self.headless)
        context = await self._browser.new_context(
            locale="ru-RU",
            storage_state=str(self.session_path),
            viewport={"width": 430, "height": 932},  # мобильная раскладка — у площадки композер иначе на десктопе
        )
        self.page = await context.new_page()
        return self

    async def __aexit__(self, *exc):
        if self._browser:
            await self._browser.close()
        if self._pw:
            await self._pw.stop()
