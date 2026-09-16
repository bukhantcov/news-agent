"""
Конвертер cookies в storage_state.json для Playwright. Логин делается руками
в обычном браузере — этот скрипт не трогает пароль, только переупаковывает
уже выданные площадкой cookies.

Два формата входа:

A) JSON-экспорт расширения Cookie-Editor (Chrome/Firefox):
    python -m uklad.social.cookies_to_state instagram ~/Downloads/instagram_cookies.json

B) Safari — Cookie-Editor не ставится, экспорт вручную через Web Inspector:
   1. Safari → Настройки → Дополнения → Show features for web developers (включить меню Разработка).
   2. На вкладке instagram.com: Разработка → Показать веб-инспектор → вкладка Storage → Cookies → instagram.com.
   3. В таблице нужны минимум: sessionid, ds_user_id, csrftoken, mid, ig_did, rur — открой
      значение каждой (клик по строке), скопируй.
   4. Сохрани текстовым файлом, по одной cookie на строку, формат name=value:

        sessionid=12345%3Aabc...
        ds_user_id=12345
        csrftoken=abcdef...
        mid=Zxxx...
        ig_did=UUID...

   5. Запусти:
        python -m uklad.social.cookies_to_state instagram ~/Downloads/instagram_cookies.txt --manual
"""

import json
import re
import sys
import time
from pathlib import Path

from uklad.social.common import SESSION_DIR

DOMAINS = {
    "threads": "threads.com",
    "instagram": "instagram.com",
}

FAR_FUTURE = int(time.time()) + 365 * 24 * 3600

SAME_SITE_MAP = {
    "strict": "Strict",
    "lax": "Lax",
    "no_restriction": "None",
    "none": "None",
    "unspecified": "Lax",
}


def convert_cookie(raw: dict) -> dict:
    expires = raw.get("expirationDate", raw.get("expires", -1))
    if raw.get("session"):
        expires = -1
    same_site_raw = str(raw.get("sameSite", "lax")).lower()
    domain = raw["domain"]
    if not domain.startswith("."):
        # Без ведущей точки cookie host-only и не уйдёт на www.* — а мы всегда ходим через www.
        domain = "." + domain
    return {
        "name": raw["name"],
        "value": raw["value"],
        "domain": domain,
        "path": raw.get("path", "/"),
        "expires": expires if expires else -1,
        "httpOnly": bool(raw.get("httpOnly", False)),
        "secure": bool(raw.get("secure", True)),
        "sameSite": SAME_SITE_MAP.get(same_site_raw, "Lax"),
    }


def parse_manual(text: str, domain: str) -> list[dict]:
    """
    Строка на cookie. Понимает два формата:
    - `name=value` (напечатано руками);
    - вставленная строка таблицы Web Inspector: колонки Имя/Значение/Domain/...
      разделены табами или несколькими пробелами — берём первые две колонки.
    """
    cookies = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue

        simple = re.match(r"^([A-Za-z0-9_]+)=(.+)$", line)
        if simple and not re.search(r"\t|\s{2,}", line):
            name, value = simple.group(1), simple.group(2)
        else:
            parts = re.split(r"\t+|\s{2,}", line)
            if len(parts) < 2:
                continue
            name, value = parts[0], parts[1]

        cookies.append({
            "name": name.strip(),
            "value": value.strip(),
            "domain": domain,
            "path": "/",
            "httpOnly": name.strip() in {"sessionid", "csrftoken"},
            "secure": True,
            "session": False,
            "expirationDate": FAR_FUTURE,
        })
    return cookies


def main() -> int:
    if len(sys.argv) not in (3, 4) or sys.argv[1] not in DOMAINS:
        print(f"Использование: python -m uklad.social.cookies_to_state {{{'|'.join(DOMAINS)}}} <файл> [--manual]")
        return 1

    platform = sys.argv[1]
    export_path = Path(sys.argv[2]).expanduser()
    manual = "--manual" in sys.argv
    domain = DOMAINS[platform]

    if manual:
        relevant = parse_manual(export_path.read_text(encoding="utf-8"), domain)
    else:
        raw_cookies = json.loads(export_path.read_text(encoding="utf-8"))
        relevant = [c for c in raw_cookies if domain in c.get("domain", "")]
    if not relevant:
        print(f"В экспорте нет cookies для домена {domain} — проверь, что экспортировал с нужной вкладки")
        return 1

    required = {"sessionid"}
    have = {c["name"] for c in relevant}
    missing = required - have
    if missing:
        print(f"Внимание: не найдены обязательные cookies {missing} — сессия может не сработать")

    state = {"cookies": [convert_cookie(c) for c in relevant], "origins": []}

    session_path = SESSION_DIR / f"{platform}_state.json"
    session_path.parent.mkdir(parents=True, exist_ok=True)
    session_path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Сохранено: {session_path} ({len(relevant)} cookies)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
