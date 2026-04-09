import requests
import json
import time
import os
import hashlib
from datetime import datetime, timedelta

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
NEWS_API_KEY = "e08eafb22acc4ad983888ecbcdb492d4"

class NewsDB:
    def __init__(self):
        self.file = "working_published.json"
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
    """Получение свежих AI новостей"""
    
    # Используем простой запрос, который точно работает
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'artificial intelligence OR AI OR нейросети',
        'language': 'en',
        'sortBy': 'publishedAt',
        'pageSize': 10,
        'apiKey': NEWS_API_KEY
    }
    
    print(f"🔍 Запрос: {params['q']}")
    
    try:
        response = requests.get(url, params=params, timeout=30)
        data = response.json()
        
        if data.get('status') == 'ok':
            articles = data.get('articles', [])
            print(f"✅ Найдено статей: {len(articles)}")
            return articles
        else:
            print(f"❌ Ошибка: {data.get('message', 'Unknown')}")
            return []
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return []

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def create_post(article):
    title = article.get('title', '')
    description = article.get('description', '')
    source = article.get('source', {}).get('name', 'Unknown')
    url_article = article.get('url', '')
    
    if not title or len(title) < 20:
        return None
    
    # Берем описание или заголовок
    content = description if description and len(description) > 100 else title
    
    if len(content) > 500:
        content = content[:497] + "..."
    
    post = f"""⚡️ **{title[:80]}**

📅 Источник: {source}

---

{content}

---

🔗 Подробнее: {url_article}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Технологии"""
    
    return post

def main():
    print("="*60)
    print("🤖 РАБОЧИЙ AI НОВОСТНОЙ АГЕНТ")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    db = NewsDB()
    
    print("\n🔍 Поиск новостей...")
    articles = get_news()
    
    if not articles:
        print("\n❌ Новостей не найдено")
        return
    
    # Ищем непрочитанные
    new_articles = []
    for article in articles:
        if not db.is_published(article.get('url', '')):
            new_articles.append(article)
    
    print(f"📊 Новых статей: {len(new_articles)}")
    
    if not new_articles:
        print("\n❌ Нет новых новостей")
        return
    
    # Публикуем первую
    article = new_articles[0]
    print(f"\n📰 Публикуем:")
    print(f"   {article.get('title', '')[:60]}...")
    
    post = create_post(article)
    
    if post and send_to_telegram(post):
        db.mark_published(article.get('url', ''))
        print("\n✅ ОПУБЛИКОВАНО! Проверьте канал")
    else:
        print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    main()
