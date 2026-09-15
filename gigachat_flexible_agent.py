import requests
import json
import time
import os
import re
from datetime import datetime
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
BASIC_AUTH_KEY = os.environ.get("BASIC_AUTH_KEY", "")

DB_FILE = "gigachat_flexible_published.json"

def get_access_token():
    """Получение токена доступа GigaChat"""
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
            token_data = response.json()
            return token_data.get('access_token')
        else:
            print(f"❌ Ошибка получения токена: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return None

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

def send_to_telegram(text, parse_mode='HTML'):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={
            'chat_id': CHANNEL_ID, 
            'text': text, 
            'parse_mode': parse_mode,
            'disable_web_page_preview': True
        }, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка Telegram: {e}")
        return False

def escape_html(text):
    if not text:
        return ""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))

def get_news_from_gigachat(access_token):
    """Получение новостей через GigaChat API"""
    
    prompt = """Ты — профессиональный новостной аналитик. 

Найди в интернете самые важные НОВОСТИ из мира ИИ (искусственный интеллект) за последние 24 часа.

Требования к новости:
1. Это должно быть КОНКРЕТНОЕ СОБЫТИЕ (релиз, анонс, обновление модели, партнерство)
2. Должны быть КОНКРЕТНЫЕ КОМПАНИИ (OpenAI, Google, Microsoft, Meta, Anthropic, NVIDIA, DeepMind)
3. Должны быть ЦИФРЫ (проценты, деньги, количество параметров, скорость)
4. НЕ публикуй обзоры, рейтинги, дайджесты, прогнозы

Для каждой новости предоставь в строгом формате:

📌 НОВОСТЬ №1
ЗАГОЛОВОК: [короткий заголовок]
ИСТОЧНИК: [название]
СУТЬ: [2-3 предложения, только факты]
ЦИФРЫ: [перечисли ключевые цифры]
ССЫЛКА: [URL статьи, если есть]

Если новостей нет — напиши "НЕТ НОВОСТЕЙ"."""

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Bearer {access_token}'
    }
    
    data = {
        'model': 'GigaChat',
        'messages': [
            {'role': 'system', 'content': 'Ты профессиональный новостной аналитик. Твоя задача — находить реальные новости из интернета. Ты умеешь искать информацию в сети. Будь краток, только факты и цифры.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 2000,
        'stream': False,
        'repetition_penalty': 1.0,
        'update_interval': 0
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=60)
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"   ✅ GigaChat ответил")
            return content
        else:
            print(f"   ❌ Ошибка API: {response.status_code}")
            return None
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return None

def parse_news_response(response_text):
    """Парсинг ответа GigaChat в список новостей"""
    if not response_text or "НЕТ НОВОСТЕЙ" in response_text:
        return []
    
    news_list = []
    blocks = response_text.split('📌')
    
    for block in blocks:
        if not block.strip():
            continue
        
        lines = block.strip().split('\n')
        news = {}
        
        for line in lines:
            if line.startswith('НОВОСТЬ №'):
                continue
            elif line.startswith('ЗАГОЛОВОК:'):
                news['title'] = line.replace('ЗАГОЛОВОК:', '').strip()
            elif line.startswith('ИСТОЧНИК:'):
                news['source'] = line.replace('ИСТОЧНИК:', '').strip()
            elif line.startswith('СУТЬ:'):
                news['summary'] = line.replace('СУТЬ:', '').strip()
            elif line.startswith('ЦИФРЫ:'):
                news['numbers'] = line.replace('ЦИФРЫ:', '').strip()
            elif line.startswith('ССЫЛКА:'):
                news['url'] = line.replace('ССЫЛКА:', '').strip()
        
        if news.get('title') and len(news.get('title', '')) > 10:
            news_list.append(news)
    
    return news_list

def create_post(news):
    """Создание HTML-поста"""
    title = escape_html(news.get('title', ''))
    source = escape_html(news.get('source', 'Unknown'))
    summary = escape_html(news.get('summary', ''))
    numbers = escape_html(news.get('numbers', ''))
    url = news.get('url', '')
    
    post = f"""⚡️ <b>{title}</b>

📅 <b>Источник:</b> {source}

<blockquote>{summary}</blockquote>
"""

    if numbers and numbers != 'Нет':
        post += f"\n📊 <b>Ключевые цифры:</b>\n<code>{numbers}</code>\n"
    
    if url and url.startswith('http'):
        post += f"\n🔗 <a href=\"{url}\">Читать полностью</a>\n"
    
    post += f"""
━━━━━━━━━━━━━━━━━━━━━━━━
📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Технологии"""
    
    return post

def main():
    print("="*70)
    print("🤖 GIGACHAT FLEXIBLE AGENT")
    print("📡 Поиск новостей за последние 24 часа")
    print("✅ HTML-разметка для Telegram")
    print("✅ Фильтрация: только события + компании + цифры")
    print(f"⏰ Старт: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*70)
    
    while True:
        print("\n🔄 Получение токена...")
        access_token = get_access_token()
        
        if not access_token:
            print("⏳ Не удалось получить токен. Жду 10 минут...")
            time.sleep(10*60)
            continue
        
        print("🔄 Поиск новостей...")
        response = get_news_from_gigachat(access_token)
        
        if not response:
            print("⏳ GigaChat не ответил. Жду 10 минут...")
            time.sleep(10*60)
            continue
        
        news_list = parse_news_response(response)
        
        if not news_list:
            print("⏳ Нет новостей за последние 24 часа. Жду 30 минут...")
            time.sleep(30*60)
            continue
        
        print(f"\n📊 Найдено новостей: {len(news_list)}")
        
        for news in news_list:
            title = news.get('title', '')
            print(f"\n📰 {title[:60]}...")
            
            if is_published(title):
                print(f"   ⏭️ Уже публиковали")
                continue
            
            post = create_post(news)
            
            if send_to_telegram(post, parse_mode='HTML'):
                mark_published(title)
                print(f"   ✅ Опубликовано!")
                print(f"\n💤 Жду 1 час до следующей публикации...")
                time.sleep(60*60)
                break
            else:
                print(f"   ❌ Ошибка публикации")

if __name__ == "__main__":
    main()
