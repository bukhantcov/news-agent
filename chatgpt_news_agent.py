import requests
import json
import time
import os
from datetime import datetime

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
OPENAI_API_KEY = "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"

DB_FILE = "chatgpt_published.json"

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
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка Telegram: {e}")
        return False

def get_news_from_chatgpt():
    """Получение новостей через ChatGPT API"""
    
    prompt = """Ты — профессиональный новостной аналитик. 

Найди в интернете (используй свои знания о последних событиях) 3 самые важные НОВОСТИ из мира ИИ (искусственный интеллект) за последние 24 часа.

Требования к новости:
1. Это должно быть КОНКРЕТНОЕ СОБЫТИЕ (релиз, анонс, обновление модели, партнерство, инвестиции)
2. Должны быть КОНКРЕТНЫЕ КОМПАНИИ (OpenAI, Google, Microsoft, Meta, Anthropic, NVIDIA и др.)
3. Должны быть ЦИФРЫ (проценты, деньги, количество параметров, скорость)
4. НЕ публикуй обзоры, рейтинги, дайджесты, "топ-10", общие статьи
5. НЕ публикуй выдуманные новости — только то, что действительно произошло

Для каждой новости предоставь в строгом формате:

📌 НОВОСТЬ №1
ЗАГОЛОВОК: [короткий заголовок, отражающий суть]
ИСТОЧНИК: [название издания или блога]
СУТЬ: [2-3 предложения, только факты]
ЦИФРЫ: [перечисли ключевые цифры через запятую]

Если за последние 24 часа нет реальных новостей — напиши "НЕТ НОВОСТЕЙ"."""

    headers = {
        'Authorization': f'Bearer {OPENAI_API_KEY}',
        'Content-Type': 'application/json'
    }
    
    data = {
        'model': 'gpt-3.5-turbo',
        'messages': [
            {'role': 'system', 'content': 'Ты профессиональный новостной аналитик. Твоя задача — находить и структурировать реальные новости.'},
            {'role': 'user', 'content': prompt}
        ],
        'temperature': 0.3,
        'max_tokens': 2000
    }
    
    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers=headers,
            json=data,
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            print(f"   ✅ ChatGPT ответил")
            return content
        else:
            print(f"   ❌ Ошибка API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return None

def parse_news_response(response_text):
    """Парсинг ответа ChatGPT в список новостей"""
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
        
        if news.get('title') and len(news.get('title', '')) > 10:
            news_list.append(news)
    
    return news_list

def create_post(news):
    """Создание поста в формате 'сухо и по делу'"""
    title = news.get('title', '')
    source = news.get('source', 'Unknown')
    summary = news.get('summary', '')
    numbers = news.get('numbers', '')
    
    post = f"""⚡️ **{title}**

📅 Источник: {source}

---

{summary}

"""

    if numbers:
        post += f"\n📊 **Ключевые цифры:** {numbers}\n"
    
    post += f"""

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Технологии"""
    
    return post

def main():
    print("="*70)
    print("🤖 CHATGPT NEWS AGENT")
    print("📡 Поиск новостей через ChatGPT API")
    print("✅ Фильтрация: только события + компании + цифры")
    print(f"⏰ Старт: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*70)
    
    while True:
        print("\n🔄 Поиск новостей...")
        
        response = get_news_from_chatgpt()
        
        if not response:
            print("⏳ ChatGPT не ответил. Жду 30 минут...")
            time.sleep(30*60)
            continue
        
        news_list = parse_news_response(response)
        
        if not news_list:
            print("⏳ Нет новостей за последние 24 часа. Жду 30 минут...")
            time.sleep(30*60)
            continue
        
        print(f"\n📊 Найдено новостей: {len(news_list)}")
        
        published = False
        for news in news_list:
            title = news.get('title', '')
            
            if is_published(title):
                print(f"   ⏭️ Уже было: {title[:50]}...")
                continue
            
            print(f"\n📰 Публикуем: {title[:60]}...")
            
            post = create_post(news)
            
            if send_to_telegram(post):
                mark_published(title)
                print(f"✅ Опубликовано!")
                published = True
                break
        
        if published:
            print("\n💤 Жду 1 час до следующей публикации...")
            time.sleep(60*60)
        else:
            print("\n⏳ Нет новых новостей. Жду 30 минут...")
            time.sleep(30*60)

if __name__ == "__main__":
    main()
