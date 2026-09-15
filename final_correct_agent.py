import feedparser
import requests
import json
import time
import os
import re
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

# ТОЛЬКО РАБОЧИЕ RSS (проверенные)
SOURCES = {
    'OpenAI': 'https://openai.com/news/rss.xml',
    'Google AI': 'https://ai.googleblog.com/feeds/posts/default',
    'Meta AI': 'https://ai.meta.com/blog/feed/',
    'Anthropic': 'https://www.anthropic.com/news/feed.xml',
    'DeepMind': 'https://deepmind.google/blog/rss/',
    'Microsoft Research': 'https://www.microsoft.com/en-us/research/blog/feed/',
}

class NewsDB:
    def __init__(self):
        self.file = "correct_published.json"
        if os.path.exists(self.file):
            with open(self.file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'urls': []}
    
    def save(self):
        with open(self.file, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def is_published(self, url):
        return url in self.db['urls']
    
    def mark_published(self, url):
        self.db['urls'].append(url)
        self.save()

def fetch_rss():
    """Парсинг RSS с правильными заголовками"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }
    
    all_news = []
    
    for name, url in SOURCES.items():
        print(f"🔍 {name}...")
        try:
            feed = feedparser.parse(url)
            
            if feed.bozo:
                print(f"   ⚠️ Проблема с RSS, но пробуем")
            
            for entry in feed.entries[:3]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                published = entry.get('published', '')
                
                if title and link and len(title) > 15:
                    all_news.append({
                        'source': name,
                        'title': title,
                        'url': link,
                        'published': published
                    })
                    print(f"   ✅ {title[:50]}...")
                    
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        time.sleep(1)
    
    return all_news

def translate_text(text):
    """Простой перевод"""
    if not text:
        return text
    
    # Словарь замен
    translations = {
        'released': 'выпустила',
        'launched': 'запустила',
        'announced': 'анонсировала',
        'introduced': 'представила',
        'unveiled': 'представила',
        'new': 'новую',
        'model': 'модель',
        'AI': 'ИИ',
        'artificial intelligence': 'искусственный интеллект',
    }
    
    result = text
    for en, ru in translations.items():
        result = re.sub(rf'\b{en}\b', ru, result, flags=re.IGNORECASE)
    
    return result

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"Ошибка: {e}")
        return False

def main():
    print("="*60)
    print("🤖 ПРАВИЛЬНЫЙ НОВОСТНОЙ АГЕНТ")
    print("📡 Только официальные RSS производителей AI")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    db = NewsDB()
    
    print("\n📡 Парсинг официальных RSS...")
    news_list = fetch_rss()
    
    if not news_list:
        print("\n❌ Новостей не найдено")
        return
    
    print(f"\n📊 Всего найдено: {len(news_list)}")
    
    # Фильтруем новые
    new_news = []
    for news in news_list:
        if not db.is_published(news['url']):
            new_news.append(news)
            print(f"   ✅ Новая: {news['title'][:50]}...")
    
    if not new_news:
        print("\n❌ Нет новых новостей")
        return
    
    # Публикуем первую
    news = new_news[0]
    title_ru = translate_text(news['title'])
    
    post = f"""⚡️ **{title_ru[:80]}**

📅 Источник: {news['source']}

---

{title_ru}

🔗 Подробнее: {news['url']}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости"""
    
    print(f"\n📰 Публикуем:")
    print(f"   {news['title'][:60]}...")
    
    if send_to_telegram(post):
        db.mark_published(news['url'])
        print("\n✅ ОПУБЛИКОВАНО!")
    else:
        print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    main()
