import os
import feedparser
import requests
import re
import time
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

# ТОЛЬКО ПРОВЕРЕННЫЕ РАБОЧИЕ RSS
SOURCES = {
    'Habr AI': 'https://habr.com/ru/rss/hub/ai/',
    'Habr ML': 'https://habr.com/ru/rss/hub/machine_learning/',
    'VC.ru': 'https://vc.ru/feed',
    'TechCrunch': 'https://techcrunch.com/feed/',
    'The Verge': 'https://www.theverge.com/rss/index.xml',
    'Wired': 'https://www.wired.com/feed/rss',
}

def get_article_text(url):
    """Простой парсинг текста статьи"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем скрипты и стили
        for tag in soup(['script', 'style', 'nav', 'header', 'footer']):
            tag.decompose()
        
        # Ищем контент
        content = soup.find('article')
        if not content:
            content = soup.find(class_=re.compile(r'content|post|entry', re.I))
        if not content:
            content = soup.find('main')
        
        if content:
            paragraphs = content.find_all('p')
            text = '\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 40])
            if len(text) > 300:
                return text[:2000]  # Ограничиваем длину
        
        return None
    except Exception as e:
        return None

def fetch_news():
    """Сбор новостей"""
    print(f"\n🔍 Сбор новостей в {datetime.now().strftime('%H:%M:%S')}")
    print("="*50)
    
    articles = []
    
    for name, url in SOURCES.items():
        print(f"\n📡 {name}:")
        try:
            feed = feedparser.parse(url)
            print(f"   Записей в ленте: {len(feed.entries)}")
            
            for entry in feed.entries[:2]:
                title = entry.get('title', '')
                link = entry.get('link', '')
                
                if not title or not link:
                    continue
                
                # Пропускаем слишком короткие заголовки
                if len(title) < 20:
                    continue
                
                # Пропускаем страницы категорий
                if any(bad in link for bad in ['/page/', '/category/', '/tag/']):
                    continue
                
                print(f"   📰 {title[:50]}...")
                
                # Получаем текст
                text = get_article_text(link)
                
                if text and len(text) > 300:
                    articles.append({
                        'source': name,
                        'title': title,
                        'text': text,
                        'url': link
                    })
                    print(f"   ✅ Текст получен ({len(text)} символов)")
                else:
                    print(f"   ⚠️ Нет текста")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return articles

def send_to_tg(text):
    """Отправка в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except:
        return False

def create_post(article):
    """Создание поста"""
    title = article['title']
    text = article['text']
    source = article['source']
    
    # Берем первые 3 предложения
    sentences = re.split(r'[.!?]+', text)
    essence = '. '.join(sentences[:3])[:500]
    
    post = f"""⚡️ **{title[:80]}**

📅 Источник: {source}

---

{essence}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости"""
    
    return post

def main():
    print("="*50)
    print("🤖 WORKING RSS AGENT")
    print("="*50)
    
    articles = fetch_news()
    
    if not articles:
        print("\n❌ Статей не найдено")
        return
    
    print(f"\n📊 Найдено статей: {len(articles)}")
    
    # Публикуем первую
    article = articles[0]
    print(f"\n📤 Публикуем: {article['title'][:50]}...")
    
    post = create_post(article)
    
    if send_to_tg(post):
        print("\n✅ ОПУБЛИКОВАНО!")
    else:
        print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    main()
