import requests
import feedparser
import json
import time
import os
import re
import hashlib
import random
from datetime import datetime
from newspaper import Article

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

# ================== НАСТРОЙКИ ==================
DB_FILE = "multi_source_db.json"

# RSS источники, которые не блокируют парсинг
SOURCES = {
    'TechCrunch': 'https://techcrunch.com/category/artificial-intelligence/feed/',
    'The Verge': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml',
    'VentureBeat': 'https://venturebeat.com/category/ai/feed/',
    'Wired': 'https://www.wired.com/feed/tag/ai/rss',
}

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'urls': []}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def is_duplicate(url):
    db = load_db()
    return url in db['urls']

def mark_published(url):
    db = load_db()
    db['urls'].append(url)
    save_db(db)

def get_full_article_text(url):
    """Парсинг полного текста"""
    try:
        article = Article(url)
        article.download()
        article.parse()
        full_text = article.text
        if full_text and len(full_text) > 500:
            print(f"      📖 Текст: {len(full_text)} символов")
            return full_text
        return None
    except Exception as e:
        print(f"      ❌ Ошибка: {e}")
        return None

def translate_to_russian(text):
    """Перевод через MyMemory"""
    if not text or re.search('[а-яА-Я]', text):
        return text
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {'q': text[:1000], 'langpair': 'en|ru', 'de': 'your_email@gmail.com'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            translated = response.json().get('responseData', {}).get('translatedText', text)
            translated = re.sub(r'\[[^\]]+\]', '', translated)
            return translated
    except Exception as e:
        print(f"      ⚠️ Ошибка перевода: {e}")
    return text

def humanize_text(text):
    """Убирает AI-признаки"""
    if not text: return ""
    patterns = [
        (r'В современном быстро меняющемся мире\s*', ''),
        (r'Стоит отметить, что\s*', ''),
        (r'Важно подчеркнуть,\s*', ''),
        (r'Таким образом,\s*', ''),
        (r'Кроме того,\s*', ''),
    ]
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

def fetch_all_news():
    """Сбор новостей из всех источников"""
    all_news = []
    for name, rss_url in SOURCES.items():
        print(f"🔍 {name}...")
        try:
            feed = feedparser.parse(rss_url)
            count = 0
            for entry in feed.entries[:5]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                pub_date = entry.get('published', '')
                if title and link:
                    all_news.append({
                        'source': name,
                        'title': title,
                        'url': link,
                        'pub_date': pub_date
                    })
                    count += 1
            print(f"   ✅ {count} новостей")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        time.sleep(1)
    return all_news

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка Telegram: {e}")
        return False

def create_post(news, full_text):
    title_ru = translate_to_russian(news['title'])
    full_text_ru = translate_to_russian(full_text)
    humanized = humanize_text(full_text_ru)
    
    if len(humanized) > 3500:
        humanized = humanized[:3497] + "..."
    
    post = f"""⚡️ **{title_ru}**

📅 Источник: {news['source']}
📅 Дата: {news['pub_date']}

---

{humanized}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Tech"""
    
    return post

def main():
    print("="*70)
    print("🤖 MULTI-SOURCE NEWS AGENT")
    print("📡 Источники: TechCrunch, The Verge, VentureBeat, Wired")
    print(f"⏰ Старт: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*70)
    
    while True:
        print("\n🔄 Новый цикл...")
        all_news = fetch_all_news()
        
        if not all_news:
            print("⏳ Нет новостей. Жду 30 минут...")
            time.sleep(30*60)
            continue
        
        # Перемешиваем, чтобы не было приоритета одного источника
        random.shuffle(all_news)
        
        for news in all_news:
            if is_duplicate(news['url']):
                print(f"   ⏭️ Дубликат: {news['title'][:50]}...")
                continue
            
            print(f"\n📰 Обрабатываем: {news['title'][:60]}...")
            full_text = get_full_article_text(news['url'])
            
            if not full_text:
                print("   ⏭️ Нет полного текста, пропускаем")
                continue
            
            post = create_post(news, full_text)
            
            if send_to_telegram(post):
                mark_published(news['url'])
                print("✅ Опубликовано! Ждем 1 час...")
                time.sleep(60*60)
                break  # Опубликовали, начинаем новый цикл
        
        print("⏳ Новостей для публикации нет. Жду 1 час...")
        time.sleep(60*60)

if __name__ == "__main__":
    main()
