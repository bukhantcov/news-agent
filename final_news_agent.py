import requests
import json
import time
import os
import re
import hashlib
import random
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

DB_FILE = "final_news_db.json"

# Список доверенных источников (только те, где есть реальные новости)
SOURCES = {
    'TechCrunch': 'https://techcrunch.com/category/artificial-intelligence/',
    'VentureBeat': 'https://venturebeat.com/category/ai/',
    'The Verge': 'https://www.theverge.com/ai-artificial-intelligence',
}

# Ключевые слова для фильтрации (должны быть в новости)
REQUIRED_KEYWORDS = [
    'openai', 'google', 'microsoft', 'meta', 'anthropic', 'deepmind',
    'gpt', 'claude', 'gemini', 'llama', 'mistral', 'midjourney',
    'выпустил', 'анонсировал', 'представил', 'запустил', 'релиз',
    'новая версия', 'обновление', 'api', 'модель', 'нейросеть'
]

# Слова-исключения (мусор)
EXCLUDE_KEYWORDS = [
    'подпишись', 'рассылка', 'дайджест', 'топ лучших', 'рейтинг',
    'обзор', 'тренды', 'как выбрать', 'для начинающих', 'введение'
]

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'urls': []}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def is_published(url):
    db = load_db()
    return url in db['urls']

def mark_published(url):
    db = load_db()
    db['urls'].append(url)
    save_db(db)

def fetch_articles():
    """Парсинг статей с источников"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    all_articles = []
    
    for name, url in SOURCES.items():
        print(f"\n🔍 {name}...")
        try:
            response = requests.get(url, headers=headers, timeout=30)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Ищем статьи
            for article in soup.find_all('article', limit=10):
                title_elem = article.find('h2') or article.find('h3')
                if not title_elem:
                    continue
                
                link_elem = title_elem.find('a')
                if not link_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                link = link_elem.get('href', '')
                
                if not link.startswith('http'):
                    link = link if link.startswith('https') else f"https://{link}"
                
                if title and link and len(title) > 25:
                    # Проверяем, что это не мусор
                    if not any(ex in title.lower() for ex in EXCLUDE_KEYWORDS):
                        all_articles.append({
                            'title': title,
                            'url': link,
                            'source': name
                        })
            
            print(f"   ✅ Найдено {len([a for a in all_articles if a['source'] == name])} статей")
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
    
    return all_articles

def get_full_article(url):
    """Парсинг полного текста статьи"""
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        response = requests.get(url, headers=headers, timeout=30)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Удаляем мусор
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()
        
        # Ищем контент
        content = soup.find('article')
        if not content:
            content = soup.find(class_=re.compile(r'content|post|entry', re.I))
        
        if content:
            paragraphs = content.find_all('p')
            text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 50])
            
            # Очищаем от мусора
            text = re.sub(r'Join.*?for free', '', text, flags=re.IGNORECASE)
            text = re.sub(r'Sign up.*?newsletter', '', text, flags=re.IGNORECASE)
            
            if len(text) > 400:
                return text
        return None
    except Exception as e:
        return None

def extract_numbers(text):
    """Извлечение цифр из текста"""
    numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(%|млн|млрд|тыс|B|M|K|долл|₽|\$)', text, re.IGNORECASE)
    return numbers[:5]

def extract_companies(text):
    """Извлечение названий компаний"""
    companies = []
    company_list = ['OpenAI', 'Google', 'Microsoft', 'Meta', 'Anthropic', 'DeepMind', 
                    'NVIDIA', 'AMD', 'Intel', 'Amazon', 'Apple', 'Mistral', 'Midjourney']
    for company in company_list:
        if company.lower() in text.lower():
            companies.append(company)
    return companies

def translate_to_russian(text):
    """Перевод через MyMemory"""
    if not text or re.search('[а-яА-Я]', text):
        return text
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {'q': text[:1000], 'langpair': 'en|ru', 'de': 'your_email@gmail.com'}
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            translated = response.json().get('responseData', {}).get('translatedText', text)
            translated = re.sub(r'\[[^\]]+\]', '', translated)
            return translated
    except:
        pass
    return text

def create_post(title, content, source, url):
    """Создание поста в формате 'сухо и по делу'"""
    
    # Извлекаем суть (первые 2-3 предложения)
    sentences = re.split(r'[.!?]+', content)
    essence = []
    for s in sentences[:4]:
        s = s.strip()
        if len(s) > 30:
            essence.append(s)
    
    summary = '. '.join(essence[:3])
    if len(summary) > 500:
        summary = summary[:497] + "..."
    
    # Извлекаем цифры для акцента
    numbers = extract_numbers(content)
    companies = extract_companies(content)
    
    # Перевод заголовка
    title_ru = translate_to_russian(title)
    
    # Формируем пост (сухо, без воды)
    post = f"""⚡️ **{title_ru}**

📅 Источник: {source}

---

{summary}

"""

    if numbers:
        post += f"\n📊 **Ключевые цифры:**\n"
        for num in numbers[:3]:
            post += f"   • {num[0]} {num[1]}\n"
    
    if companies:
        post += f"\n🏢 **Компании:** {', '.join(companies)}\n"
    
    post += f"""

🔗 {url}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Технологии"""
    
    return post

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

def main():
    print("="*70)
    print("🤖 FINAL NEWS AGENT - ТОЛЬКО КОНКРЕТНЫЕ НОВОСТИ")
    print("📡 Источники: TechCrunch, VentureBeat, The Verge")
    print("✅ Требования: компания + цифры + действие")
    print(f"⏰ Старт: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*70)
    
    while True:
        print("\n🔄 Сбор новостей...")
        
        articles = fetch_articles()
        
        if not articles:
            print("⏳ Нет статей. Жду 30 минут...")
            time.sleep(30*60)
            continue
        
        print(f"\n📊 Найдено статей: {len(articles)}")
        
        # Перемешиваем для разнообразия
        random.shuffle(articles)
        
        published = False
        for article in articles:
            if is_published(article['url']):
                print(f"   ⏭️ Уже было: {article['title'][:50]}...")
                continue
            
            print(f"\n📰 Анализ: {article['title'][:60]}...")
            
            # Проверяем заголовок на наличие ключевых слов
            title_lower = article['title'].lower()
            has_keyword = any(kw in title_lower for kw in REQUIRED_KEYWORDS)
            
            if not has_keyword:
                print(f"   ⏭️ Нет ключевых слов")
                continue
            
            # Получаем полный текст
            full_text = get_full_article(article['url'])
            
            if not full_text:
                print(f"   ⏭️ Нет полного текста")
                continue
            
            # Проверяем наличие цифр
            numbers = extract_numbers(full_text)
            if len(numbers) < 1:
                print(f"   ⏭️ Нет цифр")
                continue
            
            print(f"   ✅ Подходит для публикации")
            print(f"   📊 Цифры: {', '.join([f'{n[0]}{n[1]}' for n in numbers[:3]])}")
            
            # Создаем пост
            post = create_post(
                title=article['title'],
                content=full_text,
                source=article['source'],
                url=article['url']
            )
            
            # Публикуем
            if send_to_telegram(post):
                mark_published(article['url'])
                print(f"\n✅ ОПУБЛИКОВАНО!")
                print(f"📏 Длина: {len(post)} символов")
                published = True
                break
            else:
                print(f"   ❌ Ошибка публикации")
        
        if published:
            print("\n💤 Жду 1 час до следующей публикации...")
            time.sleep(60*60)
        else:
            print("\n⏳ Нет подходящих новостей. Жду 30 минут...")
            time.sleep(30*60)

if __name__ == "__main__":
    main()
