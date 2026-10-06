"""Publish the next queued post from polza/fresh/posts (synced 1:1 with the daily blog article) to the Polza.Digital Telegram channel."""

import html
import json
import os
import re
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).parent
POSTS_DIR = BASE_DIR / "posts"
PUBLISHED_FILE = BASE_DIR / "published.json"
TELEGRAM_LIMIT = 4096
CAPTION_LIMIT = 1024
PIN_MARKER = "-pin"


def load_published():
    if not PUBLISHED_FILE.exists():
        return []
    return json.loads(PUBLISHED_FILE.read_text(encoding="utf-8"))


def telegram(token, method, payload):
    response = requests.post(f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=30)
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"{method} failed: {data.get('description')}")
    return data["result"]


def telegram_photo(token, chat_id, cover, caption):
    with open(cover, "rb") as photo:
        response = requests.post(
            f"https://api.telegram.org/bot{token}/sendPhoto",
            data={"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"},
            files={"photo": photo},
            timeout=60,
        )
    data = response.json()
    if not data.get("ok"):
        raise RuntimeError(f"sendPhoto failed: {data.get('description')}")
    return data["result"]


def visible_length(text):
    return len(html.unescape(re.sub(r"<[^>]+>", "", text)))


def main():
    token = os.environ.get("POLZA_BOT_TOKEN")
    channel_id = os.environ.get("POLZA_CHANNEL_ID")
    if not token or not channel_id:
        print("POLZA_BOT_TOKEN or POLZA_CHANNEL_ID is not set")
        return 1

    if "--check" in sys.argv:
        bot = telegram(token, "getMe", {})
        member = telegram(token, "getChatMember", {"chat_id": channel_id, "user_id": bot["id"]})
        print(f"Bot @{bot['username']} in {channel_id}: status={member['status']}, "
              f"can_post={member.get('can_post_messages')}, can_edit={member.get('can_edit_messages')}")
        return 0

    published = load_published()
    queue = [p for p in sorted(POSTS_DIR.glob("*.html")) if p.name not in published]
    if not queue:
        print("Queue is empty")
        return 0

    post = queue[0]
    text = post.read_text(encoding="utf-8").strip()
    cover = post.with_suffix(".png")

    if cover.exists():
        # Cover goes out as the photo, the text as its caption — one message,
        # so the Dzen mirror picks the image up together with the text.
        if visible_length(text) > CAPTION_LIMIT:
            print(f"{post.name} has a cover but its text is {visible_length(text)} chars, caption limit {CAPTION_LIMIT}")
            return 1
        message = telegram_photo(token, channel_id, cover, text)
    else:
        if PIN_MARKER not in post.stem:
            print(f"::warning::{post.name} has no cover (.png) — rule: every post goes out with an image")
        if len(text) > TELEGRAM_LIMIT:
            print(f"{post.name} is {len(text)} chars, limit {TELEGRAM_LIMIT}")
            return 1
        message = telegram(token, "sendMessage", {
            "chat_id": channel_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })
    if PIN_MARKER in post.stem:
        telegram(token, "pinChatMessage", {
            "chat_id": channel_id,
            "message_id": message["message_id"],
            "disable_notification": True,
        })

    PUBLISHED_FILE.write_text(json.dumps(published + [post.name], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Published {post.name}, {len(queue) - 1} left in queue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
