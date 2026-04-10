import requests
import json
import os
import sys
import re
from datetime import datetime, time
import pytz
import urllib3
from ddgs import DDGS
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
BASIC_AUTH_KEY = os.environ.get("BASIC_AUTH_KEY")

# Рабочее время (Московское время)
WORK_START_HOUR = 9
WORK_END_HOUR = 19

if not BOT_TOKEN or not BASIC_AUTH_KEY:
    print("❌ Ошибка: отсутствуют секреты")
    sys.exit(1)

DB_FILE = "published_news.json"

def is_working_hours():
    """Проверка: сейчас рабочее время по Москве?"""
    # Устанавливаем московский часовой пояс (UTC+3)
    moscow_tz = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.now(moscow_tz)
    current_hour = now_moscow.hour
    return WORK_START_HOUR <= current_hour < WORK_END_HOUR

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'urls': [], 'titles': []}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def is_published(url, title):
    db = load_db()
    if url in db['urls']:
        return True
    normalized_title = title.lower().replace(' ', '').replace('-', '')[:50]
    for t in db['titles']:
        if normalized_title in t.lower() or t.lower() in normalized_title:
            return True
    return False

def mark_published(url, title):
    db = load_db()
    if url not in db['urls']:
        db['urls'].append(url)
    normalized_title = title.lower().replace(' ', '').replace('-', '')[:50]
    if normalized_title not in [t.lower() for t in db['titles']]:
        db['titles'].append(title)
    save_db(db)

def get_access_token():
    print("🔄 Получение токена...")
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
        if response.status_code == 200:
            print("   ✅ Токен получен")
            return response.json().get('access_token')
    except:
        pass
    return None

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text, 'parse_mode': 'HTML', 'disable_web_page_preview': True}, timeout=30)
        return r.status_code == 200
    except:
        return False

def escape_html(text):
    if not text:
        return ""
    return text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

def search_news():
    print("🔍 Поиск свежих новостей...")
    news_results = []
    try:
        with DDGS() as ddgs:
            results = ddgs.news(
                "artificial intelligence OR AI OR LLM",
                max_results=3,
                timelimit="d"
            )
            for r in results:
                news_results.append({
                    'title': r.get('title', ''),
                    'body': r.get('body', ''),
                    'url': r.get('url', ''),
                    'source': r.get('source', 'Unknown')
                })
        print(f"   ✅ Найдено {len(news_results)} новостей")
        return news_results
    except Exception as e:
        print(f"   ❌ Ошибка поиска: {e}")
        return []

def process_with_gigachat(news_list, access_token):
    if not news_list:
        return []
    
    news = news_list[0]
    prompt = f"""Перепиши эту новость ПОДРОБНО, своими словами. Сделай текст интересным и информативным (5-8 предложений).

Заголовок: {news['title']}
Текст: {news['body']}
Источник: {news['source']}
Ссылка: {news['url']}

Ответь строго в формате:
Заголовок: [оригинальный или улучшенный]
Текст: [развернутый пересказ, 5-8 предложений]
Источник: ...
Ссылка: ..."""

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    data = {'model': 'GigaChat', 'messages': [{'role': 'system', 'content': 'Ты журналист. Пересказываешь новости подробно.'}, {'role': 'user', 'content': prompt}], 'temperature': 0.5, 'max_tokens': 1500}
    
    try:
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=90)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"   ✅ GigaChat ответил")
            return content, news['url'], news['source'], news['title']
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    return None, None, None, None

def parse_news(text, fallback_url, fallback_source, fallback_title):
    if not text:
        return None
    
    news = {}
    
    title_match = re.search(r'Заголовок:\s*(.+?)(?=\nТекст:|\nИсточник:|\nСсылка:|$)', text, re.DOTALL)
    if title_match:
        news['title'] = title_match.group(1).strip()
    else:
        news['title'] = fallback_title
    
    text_match = re.search(r'Текст:\s*(.+?)(?=\nИсточник:|\nСсылка:|$)', text, re.DOTALL)
    if text_match:
        news['summary'] = text_match.group(1).strip()
    else:
        news['summary'] = text[:800]
    
    source_match = re.search(r'Источник:\s*(.+?)(?=\nСсылка:|$)', text, re.DOTALL)
    if source_match:
        news['source'] = source_match.group(1).strip()
    else:
        news['source'] = fallback_source
    
    news['url'] = fallback_url
    news['original_title'] = fallback_title
    
    return news

def create_post(news):
    title = escape_html(news.get('title', ''))
    source = escape_html(news.get('source', 'Unknown'))
    summary = escape_html(news.get('summary', ''))
    url = news.get('url', '')
    
    if len(summary) > 3500:
        summary = summary[:3497] + "..."
    
    post = f"⚡️ <b>{title}</b>\n\n📅 <b>Источник:</b> {source}\n\n{summary}"
    
    if url:
        post += f"\n\n🔗 <a href=\"{url}\">Оригинал статьи</a>"
    
    post += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n📌 @DenisBukhancov_CRM_AI\n📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}\n#AI #Новости"
    
    return post

def main():
    # Проверка рабочего времени по Москве
    moscow_tz = pytz.timezone('Europe/Moscow')
    now_moscow = datetime.now(moscow_tz)
    
    if not is_working_hours():
        print(f"⏰ Не рабочее время по Москве. Сейчас {now_moscow.strftime('%H:%M')}, работаем с {WORK_START_HOUR}:00 до {WORK_END_HOUR}:00")
        return 0
    
    print("="*60)
    print("🤖 NEWS AGENT V6 — МОСКОВСКОЕ ВРЕМЯ")
    print(f"🚀 Запуск (МСК): {now_moscow.strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"⏰ Рабочее время: {WORK_START_HOUR}:00 - {WORK_END_HOUR}:00")
    print("="*60)
    
    token = get_access_token()
    if not token:
        return 1
    
    news_list = search_news()
    if not news_list:
        print("📭 Новостей не найдено")
        return 0
    
    first_news = news_list[0]
    if is_published(first_news['url'], first_news['title']):
        print(f"⏭️ Дубликат: {first_news['title'][:50]}...")
        return 0
    
    response, original_url, original_source, original_title = process_with_gigachat(news_list, token)
    if not response:
        print("❌ GigaChat не ответил")
        return 1
    
    news = parse_news(response, original_url, original_source, original_title)
    if not news:
        print("📭 Не удалось распарсить ответ")
        return 0
    
    if send_to_telegram(create_post(news)):
        mark_published(news['url'], news['original_title'])
        print(f"✅ ОПУБЛИКОВАНО: {news['title'][:50]}...")
        return 0
    
    return 0

if __name__ == "__main__":
    # Устанавливаем pytz для работы с часовыми поясами
    try:
        import pytz
    except ImportError:
        print("⚠️ Установите pytz: pip install pytz")
        sys.exit(1)
    sys.exit(main())
