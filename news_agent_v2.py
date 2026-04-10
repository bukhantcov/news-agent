import requests
import json
import os
import sys
import re
from datetime import datetime
import urllib3
from ddgs import DDGS

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
        if response.status_code == 200:
            print("   ✅ Токен получен")
            return response.json().get('access_token')
        else:
            print(f"   ❌ Ошибка: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
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
    """Реальный поиск новостей через DuckDuckGo"""
    print("🔍 Поиск свежих новостей через DuckDuckGo...")
    
    news_results = []
    try:
        with DDGS() as ddgs:
            results = ddgs.news(
                "artificial intelligence OR AI OR LLM OR нейросети",
                max_results=10,
                timelimit="d"  # За последние 24 часа
            )
            for r in results:
                news_results.append({
                    'title': r.get('title', ''),
                    'body': r.get('body', ''),
                    'url': r.get('url', ''),
                    'date': r.get('date', ''),
                    'source': r.get('source', 'Unknown')
                })
        print(f"   ✅ Найдено {len(news_results)} новостей")
        return news_results
    except Exception as e:
        print(f"   ❌ Ошибка поиска: {e}")
        return []

def process_with_gigachat(news_list, access_token):
    """Отправляем найденные новости в GigaChat для обработки"""
    if not news_list:
        return "НЕТ НОВОСТЕЙ"
    
    # Формируем текст для GigaChat
    news_text = ""
    for i, news in enumerate(news_list[:5], 1):
        news_text += f"""
📌 НОВОСТЬ #{i}
ЗАГОЛОВОК: {news['title']}
ИСТОЧНИК: {news['source']}
СУТЬ: {news['body']}
ССЫЛКА: {news['url']}
---
"""
    
    prompt = f"""Ты — профессиональный новостной аналитик.
Проанализируй следующие новости из мира ИИ и перепиши их в моем формате.

Новости для анализа:
{news_text}

Требования:
1. Оставь только самые важные новости (максимум 3)
2. Убери маркетинговую воду, оставь только факты
3. Если новость не про ИИ или не содержит конкретики — пропусти
4. Сохрани формат:
📌 НОВОСТЬ №1
ЗАГОЛОВОК: ...
ИСТОЧНИК: ...
СУТЬ: (2-3 предложения)
ССЫЛКА: ...

Если новости не прошли фильтрацию — напиши "НЕТ НОВОСТЕЙ"."""

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    data = {
        'model': 'GigaChat',
        'messages': [
            {'role': 'system', 'content': 'Ты редактор новостей. Оставляешь только факты. Форматируешь строго по шаблону.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 2000
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=60)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"   ✅ GigaChat обработал {len(content)} символов")
            return content
        else:
            print(f"   ❌ Ошибка GigaChat: {response.status_code}")
    except Exception as e:
        print(f"   ❌ Исключение: {e}")
    return None

def parse_news(text):
    if not text or "НЕТ НОВОСТЕЙ" in text:
        return []
    news_list = []
    for block in text.split('📌'):
        if not block.strip():
            continue
        news = {}
        for line in block.strip().split('\n'):
            if line.startswith('НОВОСТЬ №'):
                continue
            elif line.startswith('ЗАГОЛОВОК:'):
                news['title'] = line.replace('ЗАГОЛОВОК:', '').strip()
            elif line.startswith('ИСТОЧНИК:'):
                news['source'] = line.replace('ИСТОЧНИК:', '').strip()
            elif line.startswith('СУТЬ:'):
                news['summary'] = line.replace('СУТЬ:', '').strip()
            elif line.startswith('ССЫЛКА:'):
                news['url'] = line.replace('ССЫЛКА:', '').strip()
        if news.get('title') and len(news['title']) > 10:
            news_list.append(news)
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

def main():
    print("="*60)
    print("🤖 NEWS AGENT V2 — С РЕАЛЬНЫМ ПОИСКОМ")
    print(f"🚀 Запуск: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    # 1. Получаем токен
    token = get_access_token()
    if not token:
        print("❌ Не удалось получить токен")
        return 1
    
    # 2. Ищем новости через DuckDuckGo
    news_list = search_news()
    if not news_list:
        print("📭 Новостей не найдено в поиске")
        return 0
    
    # 3. Обрабатываем через GigaChat
    processed = process_with_gigachat(news_list, token)
    if not processed:
        print("❌ GigaChat не обработал новости")
        return 1
    
    # 4. Парсим результат
    final_news = parse_news(processed)
    if not final_news:
        print("📭 После фильтрации новостей не осталось")
        return 0
    
    # 5. Публикуем
    for news in final_news:
        if is_published(news['title']):
            print(f"⏭️ Уже публиковали: {news['title'][:40]}...")
            continue
        
        print(f"📰 Публикуем: {news['title'][:50]}...")
        if send_to_telegram(create_post(news)):
            mark_published(news['title'])
            print("✅ ОПУБЛИКОВАНО!")
            return 0
        else:
            print("❌ Ошибка отправки")
            return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
