import feedparser
import requests
import json
import time
import os
import hashlib
import re
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
NEWS_API_KEY = "e08eafb22acc4ad983888ecbcdb492d4"

# ============================================================
# RSS ИСТОЧНИКИ (корпоративные блоги)
# ============================================================
RSS_SOURCES = {
    # Layer 1: Корпоративные блоги
    'OpenAI': 'https://openai.com/blog/rss.xml',
    'Google DeepMind': 'https://deepmind.google/blog/rss/',
    'Meta AI': 'https://ai.meta.com/blog/feed/',
    'Anthropic': 'https://www.anthropic.com/news/feed.xml',
    'Microsoft Research': 'https://www.microsoft.com/en-us/research/blog/feed/',
    'Hugging Face': 'https://huggingface.co/blog/feed.xml',
    'Mistral AI': 'https://mistral.ai/news/feed.xml',
    
    # Layer 3: Техно-СМИ (RSS)
    'TechCrunch': 'https://techcrunch.com/feed/',
    'The Verge': 'https://www.theverge.com/rss/index.xml',
    'VentureBeat': 'https://venturebeat.com/category/ai/feed/',
    
    # Layer 4: Региональные
    'Habr AI': 'https://habr.com/ru/rss/hub/ai/',
    'VC.ru': 'https://vc.ru/feed',
}

# ============================================================
# БАЗА ДАННЫХ
# ============================================================
class NewsDB:
    def __init__(self):
        self.file = "ultimate_published.json"
        self.load()
    
    def load(self):
        if os.path.exists(self.file):
            with open(self.file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'urls': [], 'titles': []}
    
    def save(self):
        with open(self.file, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def is_published(self, url, title):
        url_hash = hashlib.md5(url.encode()).hexdigest()
        title_hash = hashlib.md5(title.lower().encode()).hexdigest()
        return url in self.db['urls'] or url_hash in self.db['urls'] or title_hash in self.db['urls']
    
    def mark_published(self, url, title):
        self.db['urls'].append(url)
        self.db['urls'].append(hashlib.md5(url.encode()).hexdigest())
        self.db['urls'].append(hashlib.md5(title.lower().encode()).hexdigest())
        self.db['titles'].append(title)
        self.save()

# ============================================================
# RSS ПАРСЕР
# ============================================================
class RSSParser:
    def __init__(self):
        self.articles = []
    
    def fetch_rss(self, source_name, rss_url, limit=3):
        """Парсинг RSS ленты"""
        try:
            feed = feedparser.parse(rss_url)
            count = 0
            for entry in feed.entries:
                if count >= limit:
                    break
                
                title = entry.get('title', '')
                link = entry.get('link', '')
                published = entry.get('published', '')
                summary = entry.get('summary', '')
                
                if not title or not link:
                    continue
                
                # Пропускаем слишком короткие
                if len(title) < 20:
                    continue
                
                self.articles.append({
                    'title': title,
                    'url': link,
                    'content': summary,
                    'published': published,
                    'source': source_name,
                    'type': 'rss'
                })
                count += 1
                
        except Exception as e:
            print(f"   ❌ Ошибка RSS {source_name}: {e}")

# ============================================================
# NEWSAPI ПАРСЕР
# ============================================================
class NewsAPIParser:
    def __init__(self):
        self.articles = []
    
    def fetch_newsapi(self):
        """Получение новостей через NewsAPI"""
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': 'artificial intelligence OR AI OR нейросети',
            'language': 'en',
            'sortBy': 'publishedAt',
            'pageSize': 15,
            'apiKey': NEWS_API_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            
            if data.get('status') == 'ok':
                articles = data.get('articles', [])
                for article in articles:
                    title = article.get('title', '')
                    if not title or len(title) < 20:
                        continue
                    
                    self.articles.append({
                        'title': title,
                        'url': article.get('url', ''),
                        'content': article.get('description', ''),
                        'published': article.get('publishedAt', ''),
                        'source': article.get('source', {}).get('name', 'Unknown'),
                        'type': 'newsapi'
                    })
                print(f"   ✅ NewsAPI: {len(articles)} статей")
            else:
                print(f"   ❌ NewsAPI ошибка: {data.get('message', 'Unknown')}")
        except Exception as e:
            print(f"   ❌ NewsAPI ошибка: {e}")

# ============================================================
# ПЕРЕВОДЧИК
# ============================================================
class Translator:
    def __init__(self):
        self.cache = {}
    
    def translate(self, text):
        if not text:
            return text
        if re.search(r'[а-яА-Я]', text):
            return text
        
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]
        
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {'q': text[:500], 'langpair': 'en|ru', 'de': 'denisbuhancov@gmail.com'}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                translated = data.get('responseData', {}).get('translatedText', text)
                translated = re.sub(r'\[[^\]]+\]', '', translated)
                self.cache[text_hash] = translated
                return translated
        except:
            pass
        return text

# ============================================================
# HUMANIZER
# ============================================================
class Humanizer:
    @staticmethod
    def rewrite(title, content):
        if not content:
            content = title
        
        # Убираем шаблонные фразы
        content = re.sub(r'according to sources?|as reported by|in a blog post', '', content, flags=re.IGNORECASE)
        content = re.sub(r'согласно источникам|как сообщает|в блоге', '', content, flags=re.IGNORECASE)
        
        # Живые вступления
        intros = ["Свежая новость: ", "Обратите внимание: ", "Только что: ", "Важное обновление: "]
        
        # Извлекаем суть
        sentences = re.split(r'[.!?]+', content)
        essence = '. '.join(sentences[:2])[:350]
        
        result = random.choice(intros) + essence.lower() if essence else content
        
        emotions = [" Интересно!", " Важный шаг!", " Следим за развитием!"]
        if len(result) < 400:
            result += random.choice(emotions)
        
        return result

# ============================================================
# ОТПРАВКА В TELEGRAM
# ============================================================
def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except:
        return False

def create_post(article, translator, humanizer):
    title_ru = translator.translate(article['title'])
    
    if article.get('content'):
        content_ru = translator.translate(article['content'])
        humanized = humanizer.rewrite(title_ru, content_ru)
    else:
        humanized = title_ru
    
    post = f"""⚡️ **{title_ru[:80]}**

📅 Источник: {article['source']}
🏷 #AI #Новости

---

{humanized[:500]}

---

🔗 Подробнее: {article['url']}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AINews #TechAnalysis"""
    
    return post

# ============================================================
# ОСНОВНАЯ ФУНКЦИЯ
# ============================================================
def main():
    print("="*70)
    print("🚀 ULTIMATE NEWS AGENT")
    print("📡 RSS: OpenAI, DeepMind, Meta, Anthropic, TechCrunch, Habr")
    print("📡 NewsAPI: дополнительные источники")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*70)
    
    translator = Translator()
    humanizer = Humanizer()
    db = NewsDB()
    
    all_articles = []
    
    # 1. Парсим RSS источники
    print("\n📡 Парсинг RSS источников...")
    rss_parser = RSSParser()
    
    for name, rss_url in RSS_SOURCES.items():
        print(f"   🔍 {name}...")
        rss_parser.fetch_rss(name, rss_url, limit=2)
        time.sleep(1)
    
    all_articles.extend(rss_parser.articles)
    print(f"\n📊 RSS: найдено {len(rss_parser.articles)} статей")
    
    # 2. Парсим NewsAPI
    print("\n📡 Парсинг NewsAPI...")
    newsapi_parser = NewsAPIParser()
    newsapi_parser.fetch_newsapi()
    all_articles.extend(newsapi_parser.articles)
    print(f"📊 NewsAPI: найдено {len(newsapi_parser.articles)} статей")
    
    print(f"\n📊 Всего найдено: {len(all_articles)}")
    
    # 3. Фильтруем новые
    valid_articles = []
    for article in all_articles:
        if db.is_published(article['url'], article['title']):
            print(f"   ⏭️ Уже публиковали: {article['title'][:40]}...")
            continue
        valid_articles.append(article)
        print(f"   ✅ Новое: {article['title'][:50]}...")
    
    print(f"\n📊 Новых статей: {len(valid_articles)}")
    
    if not valid_articles:
        print("\n❌ Нет новых статей для публикации")
        return
    
    # 4. Публикуем первую
    article = valid_articles[0]
    print(f"\n📰 Публикуем из источника: {article['source']}")
    print(f"   {article['title'][:60]}...")
    
    post = create_post(article, translator, humanizer)
    
    if send_to_telegram(post):
        db.mark_published(article['url'], article['title'])
        print("\n✅ ОПУБЛИКОВАНО!")
    else:
        print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    main()
