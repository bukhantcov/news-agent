"""
Диагностика сохранённой сессии без вывода значений cookies — только имена,
длины и признаки повреждения (пробелы/переносы внутри значения — типичный
след кривого копипаста из таблицы Web Inspector).

    python -m uklad.social.inspect_session instagram
"""

import json
import sys

from uklad.social.common import SESSION_DIR


def main(platform: str) -> int:
    path = SESSION_DIR / f"{platform}_state.json"
    data = json.loads(path.read_text(encoding="utf-8"))

    for c in data["cookies"]:
        value = c["value"]
        suspicious = any(ch in value for ch in (" ", "\t", "\n", "\r"))
        print(
            f"{c['name']:<12} domain={c['domain']:<20} len={len(value):<4} "
            f"httpOnly={c['httpOnly']!s:<5} suspicious_whitespace={suspicious}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "instagram"))
