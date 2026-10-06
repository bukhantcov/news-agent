"""Build a Telegram queue post (text + cover) from a blog article.

    python polza/tools/new_post.py <path/to/blog/slug.md> archive|fresh

Writes NNN-slug.html (Telegram HTML) and NNN-slug.png (cover) into
polza/posts or polza/fresh/posts. Every post gets a cover: the Telegram
channel is mirrored to Dzen, which pulls the attached image along.

Needs Google Chrome (headless) to render the cover; set CHROME to override
the macOS default path.
"""

import html
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QUEUES = {"archive": ROOT / "posts", "fresh": ROOT / "fresh" / "posts"}
SITE = "https://polza.digital/blog/"
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
LEAD_MAX = 650

COVER = """<!doctype html><html lang="ru"><head><meta charset="utf-8">
<style>
@import url('https://fonts.googleapis.com/css2?family=PT+Serif:wght@700&family=PT+Mono:wght@400;700&display=swap');
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{width:1280px;height:720px;overflow:hidden;background:#FAF7F0}}
.c{{width:1280px;height:720px;padding:72px 88px;position:relative;display:flex;flex-direction:column;justify-content:center;color:#1A1815}}
.c::before{{content:"";position:absolute;inset:28px;border:1.5px solid rgba(26,24,21,.14)}}
.tag{{position:absolute;top:64px;left:88px;font:700 24px "PT Mono",monospace;letter-spacing:.06em;text-transform:uppercase}}
.tag i{{display:block;width:44px;height:4px;background:#C8401A;margin-top:12px}}
h1{{font:700 {size}px/1.1 "PT Serif",Georgia,serif;max-width:1040px;text-wrap:balance}}
h1 em{{font-style:normal;color:#C8401A}}
.f{{position:absolute;bottom:60px;left:88px;right:88px;display:flex;justify-content:space-between;font:400 24px "PT Mono",monospace;color:#6B6557}}
.f b{{color:#1A1815}}
</style></head><body><div class="c">
<div class="tag">{tag}<i></i></div>
<h1>{title}</h1>
<div class="f"><span><b>Polza.Digital</b></span><span>polza.digital/blog</span></div>
</div></body></html>"""


def field(text, name):
    m = re.search(rf'^{name}:\s*"((?:[^"\\]|\\.)*)"\s*$', text, re.M)
    return m.group(1).replace('\\"', '"').replace("\\\\", "\\") if m else ""


def clean(s):
    s = re.sub(r"\*\*(.+?)\*\*", r"\1", s)
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)
    return s.strip()


def trim(s, limit):
    if len(s) <= limit:
        return s
    cut = s[:limit]
    end = max(cut.rfind(". "), cut.rfind("? "), cut.rfind("! "))
    return cut[: end + 1] if end > limit // 2 else cut.rsplit(" ", 1)[0] + "…"


def highlight(title):
    safe = html.escape(title)
    num = re.search(r"(?<![\w.,:])(?!20\d\d\b)\d+(?:[.,]\d+)?(?:\s?(?:%|млрд\s?₽|млн\s?₽|₽))?(?![\w:])", safe)
    if not num:
        return safe
    return safe[: num.start()] + f"<em>{num.group(0)}</em>" + safe[num.end():]


def render_cover(title, tag, out):
    size = 88 if len(title) <= 45 else 72 if len(title) <= 70 else 60 if len(title) <= 100 else 52
    page = COVER.format(size=size, tag=html.escape(tag or "Блог"), title=highlight(title))
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(tmp) / "cover.html"
        src.write_text(page, encoding="utf-8")
        subprocess.run(
            [CHROME, "--headless", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
             "--window-size=1280,720", "--virtual-time-budget=5000", f"--screenshot={out}", f"file://{src}"],
            check=True, capture_output=True,
        )


def main():
    if len(sys.argv) != 3 or sys.argv[2] not in QUEUES:
        print(__doc__)
        return 2
    md = Path(sys.argv[1])
    folder = QUEUES[sys.argv[2]]
    slug = md.stem
    raw = md.read_text(encoding="utf-8")
    title, lead, tag = field(raw, "title"), clean(field(raw, "lead")), field(raw, "tag")
    if not title:
        print(f"no title in {md}")
        return 1

    existing = [int(m.group(1)) for p in folder.glob("*.html") if (m := re.match(r"(\d+)-", p.name))]
    stem = f"{max(existing, default=0) + 1:03d}-{slug}"

    body = f"<b>{html.escape(title)}</b>\n\n{html.escape(trim(lead, LEAD_MAX))}\n\nЧитать статью целиком: {SITE}{slug}/\n"
    (folder / f"{stem}.html").write_text(body, encoding="utf-8")
    render_cover(title, tag, folder / f"{stem}.png")
    print(f"{folder.name}/{stem}  text={len(body)} chars")
    return 0


if __name__ == "__main__":
    sys.exit(main())
