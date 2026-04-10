import requests
import json
import os
import sys
import re
from datetime import datetime
import urllib3
from ddgs import DDGS
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==================== КОНФИГУРАЦИЯ ====================
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
BASIC_AUTH_KEY = os.environ.get("BASIC_AUTH_KEY")

if not BOT_TOKEN or not BASIC_AUTH_KEY:
    print("❌ Ошибка: отсутствуют секреты")
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
    return title in load_db()['articles']

def mark_published(title):
    db = load_db()
    db['articles'].append(title)
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
                max_results=5,
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
    
    # Формируем данные
    news_text = ""
    for i, news in enumerate(news_list[:3], 1):
        news_text += f"""
НОВОСТЬ {i}:
Заголовок: {news['title']}
Текст: {news['body']}
Источник: {news['source']}
Ссылка: {news['url']}
---"""
    
    prompt = f"""Перепиши следующие новости ПОДРОБНО, своими словами. Сделай текст интересным и информативным (5-8 предложений на новость).

Новости:
{news_text}

Ответь строго в формате:

НОВОСТЬ 1:
Заголовок: [оригинальный или улучшенный]
Текст: [развернутый пересказ, 5-8 предложений]
Источник: ...
Ссылка: ...

НОВОСТЬ 2:
... и так далее.

Не добавляй лишних слов, только новости."""

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    data = {'model': 'GigaChat', 'messages': [{'role': 'system', 'content': 'Ты журналист. Пересказываешь новости подробно и интересно.'}, {'role': 'user', 'content': prompt}], 'temperature': 0.5, 'max_tokens': 2500}
    
    try:
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=90)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"   ✅ GigaChat ответил")
            return content
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
    return None

def parse_news(text):
    if not text:
        return []
    
    news_list = []
    # Разбиваем по маркеру "НОВОСТЬ"
    blocks = re.split(r'НОВОСТЬ\s*\d+:', text)
    
    for block in blocks:
        if not block.strip():
            continue
        
        news = {}
        
        # Ищем заголовок
        title_match = re.search(r'Заголовок:\s*(.+?)(?=\nТекст:|\nИсточник:|\nСсылка:|$)', block, re.DOTALL)
        if title_match:
            news['title'] = title_match.group(1).strip()
        
        # Ищем текст новости
        text_match = re.search(r'Текст:\s*(.+?)(?=\nИсточник:|\nСсылка:|$)', block, re.DOTALL)
        if text_match:
            news['summary'] = text_match.group(1).strip()
        
        # Ищем источник
        source_match = re.search(r'Источник:\s*(.+?)(?=\nСсылка:|$)', block, re.DOTALL)
        if source_match:
            news['source'] = source_match.group(1).strip()
        
        # Ищем ссылку
        url_match = re.search(r'Ссылка:\s*(.+?)(?=\n|$)', block, re.DOTALL)
        if url_match:
            news['url'] = url_match.group(1).strip()
        
        if news.get('title') and news.get('summary'):
            news_list.append(news)
    
    return news_list

def create_post(news):
    title = escape_html(news.get('title', ''))
    source = escape_html(news.get('source', 'Unknown'))
    summary = escape_html(news.get('summary', ''))
    url = news.get('url', '')
    
    if len(summary) > 3800:
        summary = summary[:3797] + "..."
    
    post = f"⚡️ <b>{title}</b>\n\n📅 <b>Источник:</b> {source}\n\n{summary}"
    
    if url:
        post += f"\n\n🔗 <a href=\"{url}\">Оригинал статьи</a>"
    
    post += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n📌 @DenisBukhancov_CRM_AI\n📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}\n#AI #Новости"
    
    return post

def main():
    print("="*60)
    print("🤖 NEWS AGENT V4.1 — ПОЛНЫЕ НОВОСТИ")
    print(f"🚀 Запуск: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    token = get_access_token()
    if not token:
        return 1
    
    news_list = search_news()
    if not news_list:
        print("📭 Новостей не найдено")
        return 0
    
    response = process_with_gigachat(news_list, token)
    if not response:
        print("❌ GigaChat не ответил")
        return 1
    
    final_news = parse_news(response)
    if not final_news:
        print("📭 Не удалось распарсить ответ")
        print(f"Ответ GigaChat: {response[:500]}")
        return 0
    
    for news in final_news:
        if is_published(news['title']):
            print(f"⏭️ Уже публиковали: {news['title'][:40]}...")
            continue
        
        if send_to_telegram(create_post(news)):
            mark_published(news['title'])
            print(f"✅ ОПУБЛИКОВАНО: {news['title'][:50]}...")
            return 0
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
