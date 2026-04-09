import requests
import re
import json
import time
import hashlib
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
NEWS_API_KEY = "e08eafb22acc4ad983888ecbcdb492d4"

# ============================================================
# БАЗА ДАННЫХ (навсегда)
# ============================================================
class NewsDatabase:
    def __init__(self):
        self.db_file = "newsapi_published.json"
        self.load()
    
    def load(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'urls': [], 'hashes': []}
    
    def save(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def is_published(self, url):
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return url in self.db['urls'] or url_hash in self.db['hashes']
    
    def mark_published(self, url):
        self.db['urls'].append(url)
        self.db['hashes'].append(hashlib.md5(url.encode()).hexdigest())
        self.save()

# ============================================================
# ПОЛУЧЕНИЕ НОВОСТЕЙ
# ============================================================
def get_ai_news():
    """Получение свежих AI новостей за последние 6 часов"""
    
    # Ищем за последние 6 часов
    since_time = (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%S')
    
    # Поисковые запросы на русском и английском
    queries = [
        'artificial intelligence breakthrough',
        'нейросети новая модель релиз',
        'OpenAI Google Microsoft AI',
        'LLM release open source',
        'AI новости технологии'
    ]
    
    all_articles = []
    
    for query in queries:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'from': (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%d'),
            'sortBy': 'publishedAt',
            'language': 'ru,en',
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
                        'published_at': article.get('publishedAt', ''),
                        'content': article.get('content', '')
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

# ============================================================
# ПАРСИНГ ПОЛНОГО ТЕКСТА
# ============================================================
def get_full_text(url):
    """Парсинг полного текста статьи"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем мусор
        for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
            tag.decompose()
        
        # Ищем контент
        content = soup.find('article')
        if not content:
            content = soup.find(class_=re.compile(r'content|post|entry|body', re.I))
        if not content:
            content = soup.find('main')
        if not content:
            content = soup.find('body')
        
        if content:
            paragraphs = content.find_all('p')
            text_parts = []
            for p in paragraphs[:15]:
                p_text = p.get_text(strip=True)
                if len(p_text) > 40:
                    text_parts.append(p_text)
            
            full_text = '\n\n'.join(text_parts)
            if len(full_text) > 400:
                return full_text[:2000]
        
        return None
    except:
        return None

# ============================================================
# ФОРМАТИРОВАНИЕ ПОСТА
# ============================================================
def create_post(article, full_text=None):
    """Создание поста в формате AI-Кардиограмма"""
    
    title = article.get('title', '')
    source = article.get('source', 'Unknown')
    description = article.get('description', '')
    
    # Используем полный текст или описание
    content = full_text if full_text else description
    
    if not content or len(content) < 100:
        return None
    
    # Берем первые 3-4 предложения
    sentences = re.split(r'[.!?]+', content)
    essence_parts = []
    for s in sentences[:4]:
        s = s.strip()
        if len(s) > 30:
            essence_parts.append(s)
    
    essence = '. '.join(essence_parts)
    if len(essence) > 500:
        essence = essence[:497] + "..."
    
    # Извлекаем технические детали
    tech_stack = extract_tech_stack(content)
    
    post = f"""⚡️ **{title[:80]}**

📅 Источник: {source}
🏷 #AI #Новости

---

🧠 **Суть**

{essence}

---

⚙️ **Технические детали**

`Архитектура:` {tech_stack['architecture']}
`Параметры:` {tech_stack['parameters']}
`Контекст:` {tech_stack['context']}

---

🔮 **Почему это важно**

Технология меняет подход к ИИ. Следим за развитием.

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AINews #TechAnalysis"""
    
    return post

def extract_tech_stack(content):
    """Извлечение технических деталей из текста"""
    tech = {'architecture': '—', 'parameters': '—', 'context': '—'}
    content_lower = content.lower()
    
    if 'transformer' in content_lower:
        tech['architecture'] = 'Transformer'
    elif 'moe' in content_lower or 'mixture of experts' in content_lower:
        tech['architecture'] = 'MoE'
    elif 'diffusion' in content_lower:
        tech['architecture'] = 'Diffusion'
    
    param_match = re.search(r'(\d+(?:\.\d+)?)\s*[Bb]', content)
    if param_match:
        tech['parameters'] = f"{param_match.group(1)}B"
    
    ctx_match = re.search(r'(\d+(?:\.\d+)?)\s*([KkMm]?)\s*токен', content_lower)
    if ctx_match:
        tech['context'] = f"{ctx_match.group(1)}{ctx_match.group(2).upper()} токенов"
    
    return tech

# ============================================================
# ОТПРАВКА В TELEGRAM
# ============================================================
def send_to_telegram(text):
    """Отправка сообщения"""
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

# ============================================================
# ГЛАВНЫЙ ЦИКЛ
# ============================================================
def run_cycle():
    """Один полный цикл (раз в 6 часов)"""
    print("="*70)
    print("🤖 FINAL NEWSAPI AGENT - ЗАПУСК ЦИКЛА")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("📡 Источник: NewsAPI")
    print("="*70)
    
    db = NewsDatabase()
    
    # 1. Получаем новости
    print("\n🔍 Поиск AI новостей...")
    articles = get_ai_news()
    
    if not articles:
        print("\n❌ Новостей не найдено")
        return
    
    print(f"\n📊 Всего найдено: {len(articles)} статей")
    
    # 2. Фильтруем непрочитанные
    new_articles = []
    for article in articles:
        if not db.is_published(article['url']):
            new_articles.append(article)
    
    print(f"📊 Новых статей: {len(new_articles)}")
    
    if not new_articles:
        print("\n❌ Нет новых статей для публикации")
        return
    
    # 3. Пробуем получить полный текст для первой статьи
    best_article = new_articles[0]
    print(f"\n🏆 Публикуем:")
    print(f"📰 {best_article['title'][:60]}...")
    print(f"🔗 {best_article['url'][:60]}...")
    
    print("\n📖 Парсинг полного текста...")
    full_text = get_full_text(best_article['url'])
    
    if full_text:
        print(f"   ✅ Получен текст ({len(full_text)} символов)")
    else:
        print(f"   ⚠️ Используем описание ({len(best_article.get('description', ''))} символов)")
    
    # 4. Создаем пост
    post = create_post(best_article, full_text)
    
    if not post:
        print("\n❌ Не удалось создать пост")
        return
    
    # 5. Публикуем
    if send_to_telegram(post):
        db.mark_published(best_article['url'])
        print("\n✅ ОПУБЛИКОВАНО!")
    else:
        print("\n❌ Ошибка публикации")
    
    print("\n" + "="*70)
    print("⏳ Следующий запуск через 6 часов")
    print("="*70)

def run_once():
    run_cycle()

def run_loop():
    while True:
        run_cycle()
        print("\n💤 Сплю 6 часов...")
        time.sleep(6 * 3600)

if __name__ == "__main__":
    import os
    run_once()
