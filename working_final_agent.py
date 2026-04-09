import requests
import xml.etree.ElementTree as ET
import json
import time
import os
import re
from datetime import datetime

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

# Прямые URL для парсинга
SOURCES = {
    'OpenAI': 'https://openai.com/news/rss.xml',
}

class NewsDB:
    def __init__(self):
        self.file = "working_final_published.json"
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

def parse_rss_manually(url):
    """Ручной парсинг RSS без feedparser"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        
        # Парсим XML вручную
        root = ET.fromstring(response.content)
        
        # Ищем все item элементы
        items = []
        for item in root.findall('.//item'):
            title_elem = item.find('title')
            title = title_elem.text if title_elem is not None else ''
            
            link_elem = item.find('link')
            link = link_elem.text if link_elem is not None else ''
            
            pubdate_elem = item.find('pubDate')
            pubdate = pubdate_elem.text if pubdate_elem is not None else ''
            
            if title and link:
                items.append({
                    'title': title,
                    'url': link,
                    'published': pubdate
                })
        
        return items
    except Exception as e:
        print(f"   ❌ Ошибка парсинга: {e}")
        return []

def translate_text(text):
    """Простой перевод"""
    if not text:
        return text
    
    translations = {
        'released': 'выпустила',
        'launched': 'запустила',
        'announced': 'анонсировала',
        'introduced': 'представила',
        'unveiled': 'представила',
        'new': 'новую',
        'model': 'модель',
        'AI': 'ИИ',
        'enterprise': 'корпоративный',
        'outlines': 'представила',
        'phase': 'этап',
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
    print("🤖 РАБОЧИЙ НОВОСТНОЙ АГЕНТ")
    print("📡 Прямой парсинг RSS OpenAI")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    db = NewsDB()
    
    print("\n📡 Парсинг RSS...")
    all_news = []
    
    for name, url in SOURCES.items():
        print(f"🔍 {name}...")
        items = parse_rss_manually(url)
        print(f"   ✅ Найдено {len(items)} новостей")
        
        for item in items[:3]:  # Берем 3 последние
            all_news.append({
                'source': name,
                'title': item['title'],
                'url': item['url'],
                'published': item['published']
            })
    
    if not all_news:
        print("\n❌ Новостей не найдено")
        return
    
    print(f"\n📊 Всего найдено: {len(all_news)}")
    
    # Фильтруем новые
    new_news = []
    for news in all_news:
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
📅 Дата: {news['published']}

---

{title_ru}

🔗 Подробнее: {news['url']}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #OpenAI"""
    
    print(f"\n📰 Публикуем:")
    print(f"   {news['title'][:60]}...")
    
    if send_to_telegram(post):
        db.mark_published(news['url'])
        print("\n✅ ОПУБЛИКОВАНО!")
        print("\n📝 Содержание поста:")
        print("-"*40)
        print(post[:400] + "...")
    else:
        print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    main()
