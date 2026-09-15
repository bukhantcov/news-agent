import os
import feedparser
import requests
import re
import json
import time
from datetime import datetime, timedelta
from newspaper import Article
from typing import List, Dict

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

# Источники (только проверенные RSS)
SOURCES = {
    # Level 1: Корпоративные блоги
    'OpenAI': 'https://openai.com/blog/rss.xml',
    'Google DeepMind': 'https://deepmind.google/blog/rss/',
    'Meta AI': 'https://ai.meta.com/blog/feed/',
    'Anthropic': 'https://www.anthropic.com/news/feed.xml',
    # Level 3: Техно-СМИ
    'TechCrunch': 'https://techcrunch.com/feed/',
    'The Verge': 'https://www.theverge.com/rss/index.xml',
    'VentureBeat': 'https://venturebeat.com/category/ai/feed/',
    # Level 4: Региональные
    'Habr': 'https://habr.com/ru/rss/all/',
    'VC.ru': 'https://vc.ru/feed',
}

# ============================================================
# ФУНКЦИИ
# ============================================================

def is_real_article(entry, source_name: str) -> bool:
    """Проверка: это конкретная статья, а не страница категории"""
    url = entry.get('link', '')
    
    # Плохие признаки (категория / лента)
    bad_signs = ['/page/', '/category/', '/tag/', '/author/', '?s=', 'search', 'archive']
    for bad in bad_signs:
        if bad in url:
            return False
    
    # Хорошие признаки (статья)
    good_signs = ['/2025/', '/2026/', '/news/', '/blog/', '/post/', 'article', 'story']
    for good in good_signs:
        if good in url:
            return True
    
    # Если URL содержит дату в формате /год/месяц/
    date_match = re.search(r'/(20\d{2})/(\d{2})/', url)
    if date_match:
        return True
    
    return len(url) > 50  # Длинный URL = скорее всего статья

def get_full_article(url: str) -> Dict:
    """Парсинг полной статьи через newspaper3k"""
    try:
        article = Article(url, language='ru')
        article.download()
        article.parse()
        
        return {
            'title': article.title,
            'text': article.text,
            'authors': article.authors,
            'publish_date': article.publish_date,
            'success': True
        }
    except Exception as e:
        return {
            'title': '',
            'text': '',
            'success': False,
            'error': str(e)
        }

def fetch_rss_feed(url: str, limit: int = 3) -> List[Dict]:
    """Получение статей из RSS ленты"""
    articles = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:limit]:
            # Проверяем, что статья сегодняшняя
            published = entry.get('published', '')
            if published:
                try:
                    pub_date = datetime(*entry.published_parsed[:6])
                    if pub_date < datetime.now() - timedelta(days=1):
                        continue  # Пропускаем старые
                except:
                    pass
            
            articles.append({
                'title': entry.get('title', ''),
                'link': entry.get('link', ''),
                'summary': entry.get('summary', ''),
                'published': published
            })
    except Exception as e:
        print(f"   ❌ Ошибка RSS {url}: {e}")
    
    return articles

def send_to_telegram(text: str) -> bool:
    """Отправка в Telegram"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except:
        return False

def create_post(title: str, content: str, source: str) -> str:
    """Создание поста в формате AI-Кардиограмма"""
    # Ограничиваем длину
    if len(content) > 1500:
        content = content[:1497] + "..."
    
    post = f"""⚡️ **{title[:80]}**

📅 Источник: {source}
🏷 #AI #Новости

---

{content}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AINews #TechAnalysis"""
    
    return post

# ============================================================
# ГЛАВНЫЙ ЗАПУСК
# ============================================================

def test_run():
    print("="*70)
    print("🧪 ТЕСТОВЫЙ ЗАПУСК АГЕНТА")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print(f"📡 Источников: {len(SOURCES)}")
    print("="*70)
    
    all_articles = []
    
    for name, rss_url in SOURCES.items():
        print(f"\n🔍 Проверяем: {name}")
        print(f"   📡 RSS: {rss_url[:60]}...")
        
        articles = fetch_rss_feed(rss_url, limit=2)
        
        for article in articles:
            # Проверяем, что это реальная статья
            if not is_real_article(article, name):
                print(f"   ⏭️ Пропущено (категория): {article['title'][:40]}...")
                continue
            
            print(f"   📰 Статья: {article['title'][:50]}...")
            
            # Парсим полный текст
            full = get_full_article(article['link'])
            
            if full['success'] and len(full['text']) > 200:
                print(f"   ✅ Получен текст: {len(full['text'])} символов")
                all_articles.append({
                    'source': name,
                    'title': full['title'] or article['title'],
                    'content': full['text'],
                    'url': article['link']
                })
            else:
                # Если парсинг не удался, используем summary
                if len(article['summary']) > 100:
                    print(f"   ⚠️ Используем summary: {len(article['summary'])} символов")
                    all_articles.append({
                        'source': name,
                        'title': article['title'],
                        'content': article['summary'],
                        'url': article['link']
                    })
                else:
                    print(f"   ❌ Не удалось получить текст")
        
        time.sleep(1)  # Пауза между запросами
    
    print("\n" + "="*70)
    print(f"📊 ИТОГО НАЙДЕНО СТАТЕЙ: {len(all_articles)}")
    print("="*70)
    
    # Публикуем первую найденную статью для теста
    if all_articles:
        test_article = all_articles[0]
        print(f"\n📤 Публикуем тестовую статью:")
        print(f"   📰 {test_article['title'][:60]}...")
        print(f"   🔗 {test_article['url']}")
        
        post = create_post(
            title=test_article['title'],
            content=test_article['content'],
            source=test_article['source']
        )
        
        if send_to_telegram(post):
            print(f"\n✅ ТЕСТОВАЯ ПУБЛИКАЦИЯ УСПЕШНА!")
            print(f"   Проверьте канал @DenisBukhancov_CRM_AI")
        else:
            print(f"\n❌ Ошибка публикации")
    else:
        print(f"\n❌ Нет статей для публикации")

if __name__ == "__main__":
    test_run()
