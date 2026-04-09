import requests
import json
import os
import sys
import re
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
BASIC_AUTH_KEY = os.environ.get("BASIC_AUTH_KEY")

# Проверка наличия секретов
if not BOT_TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден в переменных окружения")
    sys.exit(1)
if not BASIC_AUTH_KEY:
    print("❌ Ошибка: BASIC_AUTH_KEY не найден в переменных окружения")
    sys.exit(1)

DB_FILE = "published_news.json"

# ==================== БАЗА ДАННЫХ ====================
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'articles': []}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def is_published(title):
    db = load_db()
    return title in db['articles']

def mark_published(title):
    db = load_db()
    db['articles'].append(title)
    save_db(db)

# ==================== АВТОРИЗАЦИЯ ====================
def get_access_token():
    print("🔄 Получение токена GigaChat...")
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': '5f3c7b2e-4d1a-4f6b-8c9d-0e1f2a3b4c5d',
        'Authorization': f'Basic {BASIC_AUTH_KEY}'
    }
    data = {'scope': 'GIGACHAT_API_PERS'}
    try:
        response = requests.post(url, headers=headers, data=data, verify=False, timeout=30)
        print(f"   Статус: {response.status_code}")
        if response.status_code == 200:
            token = response.json().get('access_token')
            print("   ✅ Токен получен")
            return token
        else:
            print(f"   ❌ Ошибка: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
    return None

# ==================== ОТПРАВКА В TELEGRAM ====================
def send_to_telegram(text):
    print("📤 Отправка в Telegram...")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        response = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}, timeout=30)
        print(f"   Статус: {response.status_code}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def escape_html(text):
    if not text:
        return ""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

# ==================== ПОЛУЧЕНИЕ НОВОСТЕЙ ====================
def get_news(access_token):
    print("🔍 Запрос новостей к GigaChat...")
    prompt = """Ты — профессиональный новостной аналитик.

Найди в интернете 5 самых важных НОВОСТЕЙ из мира ИИ за последние 24 часа.

Используй ЭТИ источники:
- openai.com/news
- deepmind.google/blog
- ai.meta.com/blog
- anthropic.com/news
- microsoft.com/en-us/research/blog
- techcrunch.com
- theverge.com
- venturebeat.com
- wired.com

Требования:
1. КОНКРЕТНОЕ СОБЫТИЕ (релиз, анонс, обновление, партнерство)
2. КОНКРЕТНЫЕ КОМПАНИИ (OpenAI, Google, Microsoft, Meta, Anthropic)
3. НЕ публикуй обзоры, рейтинги, дайджесты

Формат:
📌 НОВОСТЬ №1
ЗАГОЛОВОК: ...
ИСТОЧНИК: ...
СУТЬ: (2-3 предложения)
ССЫЛКА: ...

Если новостей нет — напиши "НЕТ НОВОСТЕЙ"."""

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    data = {'model': 'GigaChat', 'messages': [{'role': 'system', 'content': 'Ты новостной аналитик. Ищи реальные новости. Только факты.'}, {'role': 'user', 'content': prompt}], 'temperature': 0.3, 'max_tokens': 2000}
    
    try:
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=60)
        print(f"   Статус: {response.status_code}")
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"   ✅ Получен ответ, длина: {len(content)} символов")
            return content
        else:
            print(f"   ❌ Ошибка: {response.text[:200]}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
    return None

def parse_news(text):
    if not text or "НЕТ НОВОСТЕЙ" in text:
        print("   📭 Новостей нет")
        return []
    news_list = []
    for block in text.split('📌'):
        if not block.strip():
            continue
        news = {}
        for line in block.strip().split('\n'):
            if line.startswith('ЗАГОЛОВОК:'):
                news['title'] = line.replace('ЗАГОЛОВОК:', '').strip()
            elif line.startswith('ИСТОЧНИК:'):
                news['source'] = line.replace('ИСТОЧНИК:', '').strip()
            elif line.startswith('СУТЬ:'):
                news['summary'] = line.replace('СУТЬ:', '').strip()
            elif line.startswith('ССЫЛКА:'):
                news['url'] = line.replace('ССЫЛКА:', '').strip()
        if news.get('title'):
            news_list.append(news)
    print(f"   📊 Распаршено новостей: {len(news_list)}")
    return news_list

def create_post(news):
    title = escape_html(news.get('title', ''))
    source = escape_html(news.get('source', 'Unknown'))
    summary = escape_html(news.get('summary', ''))
    url = news.get('url', '')
    
    post = f"⚡️ <b>{title}</b>\n\n📅 <b>Источник:</b> {source}\n\n<blockquote>{summary}</blockquote>"
    if url:
        post += f"\n\n🔗 <a href=\"{url}\">Читать полностью</a>"
    post += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n📌 @DenisBukhancov_CRM_AI\n📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}\n#AI #Новости #Технологии"
    return post

# ==================== ОСНОВНАЯ ФУНКЦИЯ ====================
def main():
    print("="*60)
    print("🤖 NEWS AGENT (GitHub Actions)")
    print(f"🚀 Запуск: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    token = get_access_token()
    if not token:
        print("❌ Не удалось получить токен")
        return 1
    
    response = get_news(token)
    if not response:
        print("❌ GigaChat не ответил")
        return 1
    
    news_list = parse_news(response)
    if not news_list:
        print("✅ Новостей нет — завершаем успешно")
        return 0
    
    for news in news_list:
        if is_published(news['title']):
            print(f"⏭️ Уже публиковали: {news['title'][:40]}...")
            continue
        
        print(f"📰 Публикуем: {news['title'][:50]}...")
        post = create_post(news)
        
        if send_to_telegram(post):
            mark_published(news['title'])
            print(f"✅ ОПУБЛИКОВАНО!")
            return 0
        else:
            print(f"❌ Ошибка отправки в Telegram")
            return 1
    
    print("✅ Завершено (нет новых новостей)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
