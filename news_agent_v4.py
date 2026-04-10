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
    """Реальный поиск через DuckDuckGo"""
    print("🔍 Поиск свежих новостей...")
    news_results = []
    try:
        with DDGS() as ddgs:
            results = ddgs.news(
                "artificial intelligence OR AI OR LLM OR нейросети",
                max_results=5,
                timelimit="d"
            )
            for r in results:
                news_results.append({
                    'title': r.get('title', ''),
                    'body': r.get('body', ''),
                    'url': r.get('url', ''),
                    'source': r.get('source', 'Unknown'),
                    'date': r.get('date', '')
                })
        print(f"   ✅ Найдено {len(news_results)} новостей")
        return news_results
    except Exception as e:
        print(f"   ❌ Ошибка поиска: {e}")
        return []

def get_full_article_text(url):
    """Парсинг полного текста статьи для GigaChat"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем мусор
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        # Ищем контент
        content = soup.find('article')
        if not content:
            content = soup.find(class_=re.compile(r'content|post|entry', re.I))
        
        if content:
            paragraphs = content.find_all('p')
            text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 40])
            if len(text) > 500:
                return text[:4000]  # Ограничиваем для GigaChat
        return None
    except:
        return None

def process_with_gigachat(news_list, access_token):
    """Обработка новостей через GigaChat с полным пересказом"""
    if not news_list:
        return "НЕТ НОВОСТЕЙ"
    
    # Формируем данные для GigaChat
    news_text = ""
    for i, news in enumerate(news_list[:3], 1):
        # Пробуем получить полный текст статьи
        full_text = get_full_article_text(news['url'])
        content = full_text if full_text else news['body']
        
        news_text += f"""
=== НОВОСТЬ {i} ===
ЗАГОЛОВОК: {news['title']}
ИСТОЧНИК: {news['source']}
ПОЛНЫЙ ТЕКСТ: {content}
ССЫЛКА: {news['url']}

"""
    
    prompt = f"""Ты — профессиональный журналист, специализирующийся на искусственном интеллекте.
Твоя задача: переписать следующие новости ПОДРОБНО, СВОИМИ СЛОВАМИ, без потери смысла.

Новости для переработки:
{news_text}

ПРАВИЛА:
1. Пиши развернуто, 5-10 предложений на новость
2. Сохраняй все важные детали: компании, цифры, даты
3. Используй человеческий язык, без шаблонных фраз
4. НЕ используй ссылки в тексте (они будут добавлены отдельно)
5. НЕ начинай с "Сегодня", "Недавно", "Стало известно"

Формат ответа:
📌 НОВОСТЬ №1
ЗАГОЛОВОК: (оригинальный или уточненный)
ТЕКСТ: (развернутый пересказ, 5-10 предложений)
ИСТОЧНИК: ...
ССЫЛКА: ...

Если новостей нет — напиши "НЕТ НОВОСТЕЙ"."""

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    data = {'model': 'GigaChat', 'messages': [{'role': 'system', 'content': 'Ты журналист. Пишешь подробно, интересно, с сохранением всех фактов.'}, {'role': 'user', 'content': prompt}], 'temperature': 0.5, 'max_tokens': 3000}
    
    try:
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=90)
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print(f"   ✅ GigaChat обработал")
            return content
        else:
            print(f"   ❌ Ошибка API: {response.status_code}")
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
            elif line.startswith('ТЕКСТ:'):
                news['summary'] = line.replace('ТЕКСТ:', '').strip()
            elif line.startswith('ИСТОЧНИК:'):
                news['source'] = line.replace('ИСТОЧНИК:', '').strip()
            elif line.startswith('ССЫЛКА:'):
                news['url'] = line.replace('ССЫЛКА:', '').strip()
        if news.get('title') and news.get('summary'):
            news_list.append(news)
    return news_list

def create_post(news):
    title = escape_html(news.get('title', ''))
    source = escape_html(news.get('source', 'Unknown'))
    summary = escape_html(news.get('summary', ''))
    url = news.get('url', '')
    
    # Ограничиваем длину для Telegram (4096 символов)
    if len(summary) > 3500:
        summary = summary[:3497] + "..."
    
    post = f"⚡️ <b>{title}</b>\n\n📅 <b>Источник:</b> {source}\n\n{summary}"
    
    if url:
        post += f"\n\n🔗 <a href=\"{url}\">Оригинал статьи</a>"
    
    post += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n📌 @DenisBukhancov_CRM_AI\n📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}\n#AI #Новости #Технологии"
    
    return post

def main():
    print("="*60)
    print("🤖 NEWS AGENT V4 — ПОЛНЫЕ НОВОСТИ")
    print(f"🚀 Запуск: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    token = get_access_token()
    if not token:
        return 1
    
    news_list = search_news()
    if not news_list:
        print("📭 Новостей не найдено")
        return 0
    
    processed = process_with_gigachat(news_list, token)
    if not processed:
        print("❌ GigaChat не обработал")
        return 1
    
    final_news = parse_news(processed)
    if not final_news:
        print("📭 После обработки новостей не осталось")
        return 0
    
    for news in final_news:
        if is_published(news['title']):
            print(f"⏭️ Уже публиковали: {news['title'][:40]}...")
            continue
        
        print(f"📰 Публикуем: {news['title'][:50]}...")
        if send_to_telegram(create_post(news)):
            mark_published(news['title'])
            print(f"✅ ОПУБЛИКОВАНО! ({len(news['summary'])} символов)")
            return 0
        else:
            print("❌ Ошибка отправки")
            return 1
    
    return 0

if __name__ == "__main__":
    # Импортируем BeautifulSoup для парсинга
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        print("⚠️ Установите beautifulsoup4: pip install beautifulsoup4")
        sys.exit(1)
    sys.exit(main())
