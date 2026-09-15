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

DB_FILE = "gigachat_full_published.json"

def get_access_token():
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
            return response.json().get('access_token')
    except:
        pass
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

def get_news_from_gigachat(access_token):
    prompt = """Ты — профессиональный новостной аналитик.

Найди в интернете 5 самых важных НОВОСТЕЙ из мира ИИ за последние 24 часа.

Используй ЭТИ источники (приоритет в порядке убывания):

=== КОРПОРАТИВНЫЕ БЛОГИ ===
openai.com/news, deepmind.google/blog, ai.meta.com/blog, anthropic.com/news, microsoft.com/en-us/research/blog, research.google/blog, huggingface.co/blog, mistral.ai/news, cohere.com/blog, nvidia.com/en-us/deep-learning-ai/

=== ТЕХНО-СМИ ===
techcrunch.com, theverge.com, venturebeat.com, wired.com, arstechnica.com, zdnet.com, theregister.com, analyticsindiamag.com, marktechpost.com

=== РОССИЙСКИЕ ===
habr.com, vc.ru, 3dnews.ru, cnews.ru, it-world.ru

=== ИССЛЕДОВАНИЯ ===
arxiv.org/list/cs.AI/recent, paperswithcode.com, nature.com/natmachintell

=== РАССЫЛКИ ===
tldr.tech/ai, theneurondaily.com, joinsuperhuman.ai, therundown.ai

Требования:
1. КОНКРЕТНОЕ СОБЫТИЕ (релиз, анонс, обновление, партнерство)
2. КОНКРЕТНЫЕ КОМПАНИИ (OpenAI, Google, Microsoft, Meta, Anthropic, NVIDIA, Mistral)
3. ЦИФРЫ (проценты, деньги, параметры)
4. НЕ обзоры, рейтинги, дайджесты, прогнозы

Формат:
📌 НОВОСТЬ №1
ЗАГОЛОВОК: ...
ИСТОЧНИК: ...
СУТЬ: (2-3 предложения)
ЦИФРЫ: ...
ССЫЛКА: ...

Если новостей нет — напиши "НЕТ НОВОСТЕЙ"."""

    url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
    headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'Authorization': f'Bearer {access_token}'}
    data = {'model': 'GigaChat', 'messages': [{'role': 'system', 'content': 'Ты новостной аналитик. Ищи реальные новости в указанных источниках. Только факты и цифры.'}, {'role': 'user', 'content': prompt}], 'temperature': 0.3, 'max_tokens': 2000}
    
    try:
        response = requests.post(url, headers=headers, json=data, verify=False, timeout=60)
        if response.status_code == 200:
            return response.json()['choices'][0]['message']['content']
    except:
        pass
    return None

def parse_news_response(text):
    if not text or "НЕТ НОВОСТЕЙ" in text:
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
            elif line.startswith('ЦИФРЫ:'):
                news['numbers'] = line.replace('ЦИФРЫ:', '').strip()
            elif line.startswith('ССЫЛКА:'):
                news['url'] = line.replace('ССЫЛКА:', '').strip()
        if news.get('title'):
            news_list.append(news)
    return news_list

def create_post(news):
    title = escape_html(news.get('title', ''))
    source = escape_html(news.get('source', 'Unknown'))
    summary = escape_html(news.get('summary', ''))
    numbers = escape_html(news.get('numbers', ''))
    url = news.get('url', '')
    
    post = f"⚡️ <b>{title}</b>\n\n📅 <b>Источник:</b> {source}\n\n<blockquote>{summary}</blockquote>"
    if numbers:
        post += f"\n\n📊 <b>Ключевые цифры:</b>\n<code>{numbers}</code>"
    if url:
        post += f"\n\n🔗 <a href=\"{url}\">Читать полностью</a>"
    post += f"\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n📌 @DenisBukhancov_CRM_AI\n📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}\n#AI #Новости #Технологии"
    return post

def main():
    print("="*70)
    print("🤖 GIGACHAT FULL AGENT")
    print("📡 50+ источников новостей")
    print("✅ Ежечасный постинг")
    print(f"⏰ Старт: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*70)
    
    while True:
        print("\n🔄 Получение токена...")
        token = get_access_token()
        if not token:
            time.sleep(10*60)
            continue
        
        print("🔄 Поиск новостей...")
        response = get_news_from_gigachat(token)
        if not response:
            time.sleep(10*60)
            continue
        
        news_list = parse_news_response(response)
        if not news_list:
            print("⏳ Новостей нет. Жду 30 минут...")
            time.sleep(30*60)
            continue
        
        print(f"\n📊 Найдено: {len(news_list)}")
        
        for news in news_list:
            if is_published(news['title']):
                continue
            
            if send_to_telegram(create_post(news)):
                mark_published(news['title'])
                print(f"✅ Опубликовано: {news['title'][:50]}...")
                print("\n💤 Жду 1 час...")
                time.sleep(60*60)
                break

if __name__ == "__main__":
    main()
