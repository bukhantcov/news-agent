#!/usr/bin/env python3
"""
Рендер карточки из шаблона в PNG (1080x1350) через headless Chrome.

    python3 render_card.py ustanovka --TEXT "Я всё могу" -o exports/ustanovka-01.png
    python3 render_card.py theory-quote --TEXT "..." --SOURCE "Эмиль Куэ, 1922" -o exports/t1.png
    python3 render_card.py carousel-cover --KICKER "Механика" --TITLE "6" --SUBTITLE "..." -o exports/cover.png
    python3 render_card.py ugc-quote --TEXT "..." --ATTRIBUTION "Аноним" -o exports/ugc-01.png

Плейсхолдеры в шаблоне — {{NAME}}, передаются как --NAME "значение".
Экранирует HTML-спецсимволы в подставляемом тексте (кавычки автора пишутся
как есть — это уже готовый текст, не пользовательский ввод форм).
"""

import argparse
import html
import subprocess
import sys
import tempfile
from pathlib import Path

BASE = Path(__file__).resolve().parent
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH, HEIGHT = 1080, 1350
DELAY_MS = 4000


def render(template_name: str, fields: dict, out_path: Path) -> None:
    template_path = BASE / f"{template_name}.html"
    if not template_path.exists():
        sys.exit(f"Нет шаблона {template_path}")

    html_src = template_path.read_text(encoding="utf-8")
    for key, value in fields.items():
        html_src = html_src.replace("{{" + key + "}}", html.escape(value, quote=False))

    remaining = [line for line in html_src.splitlines() if "{{" in line]
    if remaining:
        print("Внимание — не заполненные плейсхолдеры:", remaining, file=sys.stderr)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".html", delete=False, encoding="utf-8") as tmp:
        tmp.write(html_src)
        tmp_path = tmp.name

    try:
        subprocess.run(
            [
                CHROME, "--headless", "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
                f"--window-size={WIDTH},{HEIGHT}",
                f"--virtual-time-budget={DELAY_MS}",
                f"--screenshot={out_path}",
                f"file://{tmp_path}",
            ],
            check=True,
            capture_output=True,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    print(f"Готово: {out_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("template", choices=["ustanovka", "theory-quote", "carousel-cover", "ugc-quote"])
    parser.add_argument("-o", "--out", required=True, help="путь к выходному .png")
    args, unknown = parser.parse_known_args()

    fields = {}
    i = 0
    while i < len(unknown):
        if unknown[i].startswith("--"):
            key = unknown[i][2:]
            value = unknown[i + 1] if i + 1 < len(unknown) else ""
            fields[key] = value
            i += 2
        else:
            i += 1

    render(args.template, fields, Path(args.out))


if __name__ == "__main__":
    main()
