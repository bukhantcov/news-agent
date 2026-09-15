import requests
import re
import json
import time
import hashlib
import os
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
NEWS_API_KEY = "e08eafb22acc4ad983888ecbcdb492d4"

class NewsDB:
    def __init__(self):
        self.file = "published_newsapi.json"
        self.load()
    
    def load(self):
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

def get_news():
    """Получение свежих новостей"""
    
    queries = [
        '("artificial intelligence" OR "AI" OR "нейросети")',
        '("machine learning" OR "deep learning")',
        '(OpenAI OR Google AI OR Microsoft AI OR Meta AI)',
        '("LLM" OR "language model" OR "large language model")'
    ]
    
    all_articles = []
    
    for query in queries:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'language': 'ru,en',
            'sortBy': 'publishedAt',
            'pageSize': 5,
            'apiKey': NEWS_API_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('status') == 'ok':
                articles = data.get('articles', [])
                for article in articles:
                    all_articles.append({
                        'title': article.get('title', ''),
                        'description': article.get('description', ''),
                        'url': article.get('url', ''),
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'published': article.get('publishedAt', '')
                    })
                print(f"   ✅ {query[:30]}... -> {len(articles)} статей")
            else:
                print(f"   ⚠️ {query[:30]}... -> {data.get('message', 'Error')}")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        time.sleep(1)
    
    # Удаляем дубликаты по URL
    unique = []
    seen = set()
    for article in all_articles:
        if article['url'] not in seen:
            seen.add(article['url'])
            unique.append(article)
    
    return unique

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def create_post(article):
    title = article.get('title', '')
    description = article.get('description', '')
    source = article.get('source', 'Unknown')
    
    if not title or len(title) < 20:
        return None
    
    # Берем описание или заголовок как суть
    content = description if description and len(description) > 100 else title
    
    if len(content) > 500:
        content = content[:497] + "..."
    
    post = f"""⚡️ **{title[:80]}**

📅 Источник: {source}

---

{content}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Технологии"""
    
    return post

def main():
    print("="*60)
    print("🤖 AI НОВОСТНОЙ АГЕНТ")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    db = NewsDB()
    
    print("\n🔍 Поиск новостей...")
    articles = get_news()
    
    if not articles:
        print("\n❌ Новостей не найдено")
        return
    
    print(f"\n📊 Всего найдено: {len(articles)}")
    
    # Ищем непрочитанные
    new_articles = [a for a in articles if not db.is_published(a['url'])]
    print(f"📊 Новых: {len(new_articles)}")
    
    if not new_articles:
        print("\n❌ Нет новых новостей")
        return
    
    # Публикуем первую
    article = new_articles[0]
    print(f"\n📰 Публикуем:")
    print(f"   {article['title'][:60]}...")
    
    post = create_post(article)
    
    if post and send_to_telegram(post):
        db.mark_published(article['url'])
        print("\n✅ ОПУБЛИКОВАНО!")
    else:
        print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    main()
