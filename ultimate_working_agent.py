import requests
import xml.etree.ElementTree as ET
import json
import time
import os
import re
import hashlib
import random
from datetime import datetime
from newspaper import Article

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

# === 1. ПАРСИНГ RSS (РАБОТАЕТ) ===
def parse_openai_rss():
    """Парсит RSS OpenAI и возвращает список новостей."""
    url = "https://openai.com/news/rss.xml"
    news_list = []
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        root = ET.fromstring(response.content)
        for item in root.findall('.//item'):
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            news_list.append({'title': title, 'link': link, 'pub_date': pub_date})
        print(f"   ✅ OpenAI RSS: {len(news_list)} новостей")
        return news_list
    except Exception as e:
        print(f"   ❌ Ошибка парсинга RSS: {e}")
        return []

# === 2. ПАРСИНГ ПОЛНОГО ТЕКСТА (ФИКС) ===
def get_full_article_text(url):
    """Извлекает полный текст статьи через newspaper3k."""
    try:
        article = Article(url)
        article.download()
        article.parse()
        full_text = article.text
        if full_text and len(full_text) > 500:
            print(f"      📖 Текст получен ({len(full_text)} символов)")
            return full_text
        else:
            print(f"      ⚠️ Текст слишком короткий или не получен.")
            return None
    except Exception as e:
        print(f"      ❌ Ошибка парсинга статьи: {e}")
        return None

# === 3. БАЗА ДАННЫХ (чтобы не дублировать) ===
DB_FILE = "ultimate_working_db.json"
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'urls': []}
def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)
def is_duplicate(url):
    db = load_db()
    return url in db['urls']
def mark_published(url):
    db = load_db()
    db['urls'].append(url)
    save_db(db)

# === 4. ХУДОЖЕСТВЕННЫЙ ПЕРЕВОД ===
def translate_to_russian(text):
    """Переводит текст на художественный русский через MyMemory API."""
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
    except Exception as e:
        print(f"      ⚠️ Ошибка перевода: {e}")
    return text

# === 5. HUMANIZER ===
def humanize_text(text):
    """Убирает явные признаки AI-текста."""
    if not text: return ""
    # Убираем шаблонные фразы
    patterns = [
        (r'В современном быстро меняющемся мире\s*', ''),
        (r'Стоит отметить, что\s*', ''),
        (r'Важно подчеркнуть,\s*', ''),
        (r'Таким образом,\s*', ''),
        (r'Кроме того,\s*', ''),
        (r'Более того,\s*', ''),
        (r'Я надеюсь, это поможет!', ''),
        (r'Дайте мне знать, если я могу чем-то еще помочь!', ''),
        (r'Это отличный вопрос!', ''),
    ]
    for pattern, repl in patterns:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    # Чистим множественные переносы
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# === 6. ФОРМИРОВАНИЕ ПОСТА ===
def create_post(news):
    title_ru = translate_to_russian(news['title'])
    full_text_ru = translate_to_russian(news['full_text'])
    humanized_text = humanize_text(full_text_ru)
    if len(humanized_text) > 3500:
        humanized_text = humanized_text[:3497] + "..."
    
    post = f"""⚡️ **{title_ru}**

📅 Источник: OpenAI
📅 Дата: {news['pub_date']}

---

{humanized_text}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #OpenAI"""
    return post

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except Exception as e:
        print(f"   ❌ Ошибка Telegram: {e}")
        return False

# === 7. ГЛАВНЫЙ ЦИКЛ (1 ПОСТ В ЧАС) ===
def main():
    print("="*70)
    print("🤖 ULTIMATE WORKING AI AGENT")
    print("⚙️  Источник: OpenAI RSS -> Полный текст -> Перевод -> Humanizer -> Пост в Telegram")
    print(f"⏰ Старт: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*70)
    
    while True:
        print("\n🔄 Новый цикл...")
        raw_news = parse_openai_rss()
        if not raw_news:
            print("⏳ Нет новостей. Жду 30 мин...")
            time.sleep(30*60)
            continue
        
        for news in raw_news:
            if is_duplicate(news['link']):
                print(f"   ⏭️ Пропускаем дубликат: {news['title'][:50]}...")
                continue
            
            print(f"\n📰 Обрабатываем: {news['title'][:60]}...")
            full_text = get_full_article_text(news['link'])
            if not full_text:
                continue
            
            news['full_text'] = full_text
            final_post = create_post(news)
            
            if send_to_telegram(final_post):
                mark_published(news['link'])
                print("✅ Опубликовано! Ждем 1 час...")
                time.sleep(60*60)
                break  # Опубликовали, начинаем новый цикл
            
            print("   ⏭️ Ошибка публикации, пробуем следующую новость...")
        
        print("⏳ Новостей для публикации нет. Ждем 1 час...")
        time.sleep(60*60)

if __name__ == "__main__":
    main()
