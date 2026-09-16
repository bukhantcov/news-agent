"""
Разведка вёрстки: открывает страницу под сохранённой сессией, делает
скриншот и печатает accessibility-дерево кликабельных элементов — чтобы
не гадать селекторы для постинга вслепую.

    python -m uklad.social.recon instagram https://www.instagram.com/
    python -m uklad.social.recon threads https://www.threads.com/
"""

import asyncio
import sys
from pathlib import Path

from uklad.social.common import SESSION_DIR, PostSession

OUT_DIR = Path(__file__).resolve().parent / "session" / "recon"


async def main(platform: str, url: str) -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session_path = SESSION_DIR / f"{platform}_state.json"

    async with PostSession(session_path, headless=True) as session:
        await session.page.goto(url, wait_until="domcontentloaded", timeout=30_000)
        await session.page.wait_for_timeout(3000)

        shot_path = OUT_DIR / f"{platform}_{Path(url).name or 'home'}.png"
        try:
            await session.page.screenshot(path=str(shot_path), full_page=False, timeout=10_000)
            print(f"Скриншот: {shot_path}")
        except Exception as e:
            print(f"Скриншот не удался ({e}) — продолжаю без него")

        interactive = await session.page.evaluate("""
            () => Array.from(document.querySelectorAll(
                'button, a[role="link"], [role="button"], svg[aria-label], input, textarea, div[role="textbox"]'
            )).slice(0, 60).map(el => ({
                tag: el.tagName,
                role: el.getAttribute('role'),
                aria: el.getAttribute('aria-label'),
                placeholder: el.getAttribute('placeholder'),
                text: (el.innerText || '').trim().slice(0, 40),
            }))
        """)
        for el in interactive:
            print(el)

    return 0


if __name__ == "__main__":
    platform = sys.argv[1] if len(sys.argv) > 1 else "instagram"
    url = sys.argv[2] if len(sys.argv) > 2 else f"https://www.{platform}.com/"
    sys.exit(asyncio.run(main(platform, url)))
