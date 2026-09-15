import requests
import feedparser
import json
import time
import os
import hashlib
import re
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

# ============================================================
# ТОЛЬКО ДОВЕРЕННЫЕ ИСТОЧНИКИ
# ============================================================
TRUSTED_SOURCES = {
    # Корпоративные блоги (САМЫЕ ПЕРВЫЕ НОВОСТИ)
    'OpenAI': {
        'url': 'https://openai.com/news/rss.xml',
        'type': 'rss',
        'priority': 1
    },
    'Google DeepMind': {
        'url': 'https://deepmind.google/blog/rss/',
        'type': 'rss',
        'priority': 1
    },
    'Meta AI': {
        'url': 'https://ai.meta.com/blog/feed/',
        'type': 'rss',
        'priority': 1
    },
    'Anthropic': {
        'url': 'https://www.anthropic.com/news/feed.xml',
        'type': 'rss',
        'priority': 1
    },
    'Microsoft AI': {
        'url': 'https://www.microsoft.com/en-us/research/blog/feed/',
        'type': 'rss',
        'priority': 1
    },
    'Mistral AI': {
        'url': 'https://mistral.ai/news/feed.xml',
        'type': 'rss',
        'priority': 1
    },
    'Hugging Face': {
        'url': 'https://huggingface.co/blog/feed.xml',
        'type': 'rss',
        'priority': 2
    },
    # Техно-СМИ (проверенные)
    'TechCrunch': {
        'url': 'https://techcrunch.com/feed/',
        'type': 'rss',
        'priority': 2
    },
    'VentureBeat': {
        'url': 'https://venturebeat.com/category/ai/feed/',
        'type': 'rss',
        'priority': 2
    }
}

# Слова для фильтрации мусора
GARBAGE_TITLES = [
    'pypi', 'pip install', 'github.com', 'docker', 'npm', 
    'openjali', 'asyncio', 'cryptography', 'lib',
    'deprecated', 'patch release', 'bug fix', 'hotfix'
]

# Реальные AI компании и модели
REAL_AI_KEYWORDS = [
    'gpt', 'claude', 'gemini', 'llama', 'mistral', 'deepseek',
    'openai', 'anthropic', 'deepmind', 'google ai', 'meta ai',
    'neural', 'transformer', 'diffusion', 'llm', 'large language',
    'агент', 'нейросет', 'искусственный интеллект'
]

class TrustedNewsAgent:
    def __init__(self):
        self.db_file = "trusted_published.json"
        self.load_db()
        self.articles = []
    
    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'urls': [], 'titles': []}
    
    def save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def is_published(self, url):
        return url in self.db['urls']
    
    def mark_published(self, url):
        self.db['urls'].append(url)
        self.save_db()
    
    def is_real_ai_news(self, title, content):
        """Проверка: это реальная AI новость?"""
        text = (title + " " + content).lower()
        
        # Проверка на мусор
        for garbage in GARBAGE_TITLES:
            if garbage in text:
                return False
        
        # Проверка на реальные AI ключевые слова
        for keyword in REAL_AI_KEYWORDS:
            if keyword in text:
                return True
        
        return False
    
    def fetch_rss(self, source_name, rss_url):
        """Парсинг RSS"""
        try:
            feed = feedparser.parse(rss_url)
            for entry in feed.entries[:3]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                summary = entry.get('summary', '')
                
                if not title or not link:
                    continue
                
                # Проверяем, что это реальная AI новость
                if not self.is_real_ai_news(title, summary):
                    continue
                
                self.articles.append({
                    'source': source_name,
                    'title': title,
                    'url': link,
                    'content': summary,
                    'published': entry.get('published', '')
                })
        except Exception as e:
            print(f"   ❌ Ошибка {source_name}: {e}")
    
    def get_full_content(self, url):
        """Получение полного текста статьи"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'}
            response = requests.get(url, headers=headers, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
                tag.decompose()
            
            content = soup.find('article')
            if not content:
                content = soup.find(class_=re.compile(r'content|post|entry', re.I))
            
            if content:
                paragraphs = content.find_all('p')
                text = ' '.join([p.get_text(strip=True) for p in paragraphs[:10] if len(p.get_text()) > 40])
                if len(text) > 200:
                    return text
            return None
        except:
            return None
    
    def send_to_telegram(self, text):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
            return r.status_code == 200
        except:
            return False
    
    def create_post(self, article):
        title = article['title']
        content = article['content']
        source = article['source']
        url = article['url']
        
        # Берем первые 2 предложения
        sentences = re.split(r'[.!?]+', content)
        essence = '. '.join(sentences[:2])[:400]
        
        post = f"""⚡️ **{title[:80]}**

📅 Источник: {source}

---

{essence}

---

🔗 Подробнее: {url}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Нейросети"""
        
        return post
    
    def run(self):
        print("="*70)
        print("🤖 TRUSTED NEWS AGENT")
        print("📡 Источники: OpenAI, DeepMind, Meta, Anthropic, Microsoft, TechCrunch")
        print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("="*70)
        
        # Парсим все доверенные источники
        for name, info in TRUSTED_SOURCES.items():
            print(f"\n🔍 {name}...")
            self.fetch_rss(name, info['url'])
            time.sleep(1)
        
        print(f"\n📊 Всего найдено статей: {len(self.articles)}")
        
        # Фильтруем по дублям
        new_articles = []
        for article in self.articles:
            if not self.is_published(article['url']):
                new_articles.append(article)
                print(f"   ✅ {article['title'][:50]}...")
        
        print(f"\n📊 Новых статей: {len(new_articles)}")
        
        if not new_articles:
            print("\n❌ Нет новых статей для публикации")
            return
        
        # Публикуем первую
        article = new_articles[0]
        print(f"\n📰 Публикуем:")
        print(f"   {article['title'][:60]}...")
        
        post = self.create_post(article)
        
        if self.send_to_telegram(post):
            self.mark_published(article['url'])
            print("\n✅ ОПУБЛИКОВАНО!")
        else:
            print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    agent = TrustedNewsAgent()
    agent.run()
