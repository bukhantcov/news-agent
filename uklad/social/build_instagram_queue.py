#!/usr/bin/env python3
"""
Разовый билд uklad/social/instagram_queue.json из уже опубликованных/
запланированных постов uklad/posts/*.html.

Текст карточки берётся в таком порядке:
1. Отдельный абзац-цитата <i>...</i> (не инлайн внутри предложения) — тогда
   этот абзац убирается из подписи, картинка его уже несёт.
2. Иначе — заголовок поста (первый абзац, целиком <b>...</b>), если он
   короче 70 символов (влезает в дизайн карточки без переполнения) — тогда
   заголовок ОСТАЁТСЯ и в подписи (обычная практика IG: хук сверху).

Посты без того и другого (нет цитаты, заголовок длиннее лимита) —
пропускаются: лучше меньше постов, чем кривая карточка.

Строка "Приложение: rustore..." — telegram-CTA, из подписи IG убирается
(content-plan.md §1.1: на IG прямых CTA на установку не публикуем).

    python3 build_instagram_queue.py
"""

import json
import re
from pathlib import Path

POSTS_DIR = Path(__file__).resolve().parent.parent / "posts"
OUT_PATH = Path(__file__).resolve().parent / "instagram_queue.json"

TAG_RE = re.compile(r"</?[bi]>")
QUOTE_PARA_RE = re.compile(r"^<i>(?!Источник)(.+)</i>$", re.DOTALL)
SOURCE_PARA_RE = re.compile(r"^<i>Источник[и]?:\s*(.+)</i>$", re.DOTALL)
TITLE_PARA_RE = re.compile(r"^<b>(.+)</b>$", re.DOTALL)
TITLE_MAX_LEN = 70


def strip_tags(s: str) -> str:
    return TAG_RE.sub("", s).strip()


def extract(path: Path):
    paragraphs = [p.strip() for p in path.read_text(encoding="utf-8").split("\n\n") if p.strip()]
    if not paragraphs:
        return None

    # 1. Найти отдельный абзац-цитату и абзац-источник где угодно в тексте.
    quote_idx = None
    source = ""
    for i, p in enumerate(paragraphs):
        m = SOURCE_PARA_RE.match(p)
        if m:
            source = strip_tags(m.group(1))
            continue
        m = QUOTE_PARA_RE.match(p)
        if m and quote_idx is None:
            quote_idx = i

    drop_indices = set()
    text = None
    if quote_idx is not None:
        text = strip_tags(QUOTE_PARA_RE.match(paragraphs[quote_idx]).group(1))
        drop_indices.add(quote_idx)
    else:
        m = TITLE_PARA_RE.match(paragraphs[0])
        if m:
            candidate = strip_tags(m.group(1))
            if len(candidate) <= TITLE_MAX_LEN:
                text = candidate
                # заголовок остаётся в подписи — не дропаем индекс 0

    if text is None:
        return None

    keep = []
    for i, p in enumerate(paragraphs):
        if i in drop_indices:
            continue
        if SOURCE_PARA_RE.match(p):
            continue
        if p.startswith("Приложение:"):
            continue
        keep.append(strip_tags(p))

    caption = "\n\n".join(keep)
    return text, source, caption


def main():
    entries = []
    skipped = []
    for path in sorted(POSTS_DIR.glob("*.html")):
        result = extract(path)
        if result is None:
            skipped.append(path.name)
            continue
        text, source, caption = result
        entries.append({
            "post": path.stem,
            "template": "theory-quote",
            "fields": {"TEXT": text, "SOURCE": source},
            "caption": caption,
        })

    OUT_PATH.write_text(json.dumps(entries, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"В очередь: {len(entries)} постов -> {OUT_PATH}")
    print(f"Пропущено: {len(skipped)}")
    for name in skipped:
        print(f"  - {name}")


if __name__ == "__main__":
    main()
