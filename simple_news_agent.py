import feedparser
import requests
import re
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

# ТОП-10 источников для теста
SOURCES = {
    'OpenAI': 'https://openai.com/blog/rss.xml',
    'DeepMind': 'https://deepmind.google/blog/rss/',
    'Meta AI': 'https://ai.meta.com/blog/feed/',
    'TechCrunch AI': 'https://techcrunch.com/category/artificial-intelligence/feed/',
    'The Verge AI': 'https://www.theverge.com/rss/ai-artificial-intelligence/index.xml',
    'VentureBeat AI': 'https://venturebeat.com/category/ai/feed/',
    'Habr AI': 'https://habr.com/ru/rss/hub/ai/',
    'VC.ru AI': 'https://vc.ru/feed/tag/ai',
}

def get_full_text(url):
    """Парсинг полного текста статьи"""
    try:
        response = requests.get(url, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем мусор
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        # Ищем основной контент
        content = soup.find('article')
        if not content:
            content = soup.find(class_=re.compile(r'content|post|entry', re.I))
        if not content:
            content = soup.find('main')
        if not content:
            content = soup.find('body')
        
        if content:
            paragraphs = content.find_all('p')
            text_parts = []
            for p in paragraphs:
                p_text = p.get_text(strip=True)
                if len(p_text) > 30:
                    text_parts.append(p_text)
            
            full_text = '\n\n'.join(text_parts[:15])  # Первые 15 параграфов
            
            # Проверка, что текст не обрезан
            if len(full_text) > 400 and not full_text.endswith('...'):
                return full_text
        
        return None
    except Exception as e:
        print(f"   Ошибка парсинга: {e}")
        return None

def fetch_news():
    """Сбор новостей из всех источников"""
    print(f"\n🔍 Сбор новостей...")
    print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
    print("="*50)
    
    articles = []
    
    for name, url in SOURCES.items():
        print(f"\n📡 {name}:")
        
        try:
            feed = feedparser.parse(url)
            print(f"   Найдено записей: {len(feed.entries)}")
            
            for entry in feed.entries[:2]:  # 2 последние записи
                title = entry.get('title', '')
                link = entry.get('link', '')
                published = entry.get('published', '')
                
                # Пропускаем слишком короткие заголовки
                if len(title) < 15:
                    continue
                
                # Пропускаем страницы категорий
                if any(bad in link for bad in ['/page/', '/category/', '/tag/', '/author/']):
                    print(f"   ⏭️ Пропущено (категория): {title[:40]}...")
                    continue
                
                print(f"   📰 Статья: {title[:50]}...")
                
                # Получаем полный текст
                full_text = get_full_text(link)
                
                if full_text and len(full_text) > 400:
                    articles.append({
                        'source': name,
                        'title': title,
                        'text': full_text,
                        'url': link,
                        'date': published
                    })
                    print(f"   ✅ Текст получен ({len(full_text)} символов)")
                else:
                    print(f"   ⚠️ Не удалось получить полный текст")
            
            time.sleep(1)
            
        except Exception as e:
            print(f"   ❌ Ошибка RSS: {e}")
    
    return articles

def send_to_telegram(text):
    """Отправка в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"Ошибка отправки: {e}")
        return False

def create_post(article):
    """Создание поста"""
    title = article['title']
    text = article['text']
    source = article['source']
    
    # Ограничиваем длину
    if len(text) > 1200:
        text = text[:1197] + "..."
    
    # Берем первые 3-4 предложения для сути
    sentences = re.split(r'[.!?]+', text)
    essence_parts = []
    for s in sentences[:3]:
        s = s.strip()
        if len(s) > 30:
            essence_parts.append(s)
    
    essence = '. '.join(essence_parts)
    
    post = f"""⚡️ **{title[:80]}**

📅 Источник: {source}
🏷 #AI #Новости

---

**Суть**

{essence}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AINews #TechNews"""
    
    return post

def main():
    print("="*60)
    print("🤖 SIMPLE NEWS AGENT - ТЕСТ")
    print("="*60)
    
    # Сбор новостей
    articles = fetch_news()
    
    if not articles:
        print("\n❌ Новостей не найдено")
        return
    
    print("\n" + "="*60)
    print(f"📊 НАЙДЕНО СТАТЕЙ: {len(articles)}")
    print("="*60)
    
    # Публикуем первую
    article = articles[0]
    print(f"\n📤 Публикуем:")
    print(f"   {article['title'][:60]}...")
    print(f"   {article['url']}")
    
    post = create_post(article)
    
    if send_to_telegram(post):
        print("\n✅ ОПУБЛИКОВАНО!")
        print("   Проверьте канал @DenisBukhancov_CRM_AI")
    else:
        print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    main()
