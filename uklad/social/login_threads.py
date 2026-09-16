"""
Разовый вход в Threads под аккаунтом Уклад. Видимое окно — логинишься сам,
пароль здесь не вводится и не сохраняется. Сессия ложится в
uklad/social/session/threads_state.json и переиспользуется постером.

    python -m uklad.social.login_threads
"""

import asyncio
import logging

from uklad.social.common import SESSION_DIR, login_and_save_session

logging.basicConfig(level="INFO", format="%(asctime)s %(levelname)s %(name)s: %(message)s")

LOGIN_URL = "https://www.threads.com/login"
SESSION_PATH = SESSION_DIR / "threads_state.json"


async def main() -> None:
    if SESSION_PATH.exists():
        print(f"Сессия уже есть: {SESSION_PATH}")
        print("Перелогин перезапишет её. Продолжить? [y/N] ", end="")
        if input().strip().lower() != "y":
            return

    print("Откроется окно браузера. Войдите в аккаунт Уклад вручную — ждём до 5 минут.")
    ok = await login_and_save_session(LOGIN_URL, SESSION_PATH)
    print("Готово, сессия сохранена." if ok else "Вход не обнаружен, сессия не сохранена.")


if __name__ == "__main__":
    asyncio.run(main())
