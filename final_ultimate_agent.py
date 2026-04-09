import requests
import json
import time
import os
import re
import hashlib
from datetime import datetime, timedelta
from newspaper import Article
import random

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
NEWS_API_KEY = "e08eafb22acc4ad983888ecbcdb492d4"

# БАЗА ДАННЫХ (чтобы не постить одно и то же дважды)
DB_FILE = "final_ultimate_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {'urls': [], 'hashes': []}

def save_db(db):
    with open(DB_FILE, 'w') as f:
        json.dump(db, f, indent=2)

def is_duplicate(url, title):
    db = load_db()
    url_hash = hashlib.md5(url.encode()).hexdigest()
    title_hash = hashlib.md5(title.encode()).hexdigest()
    if url in db['urls'] or url_hash in db['urls'] or title_hash in db['urls']:
        return True
    return False

def mark_published(url, title):
    db = load_db()
    db['urls'].append(url)
    db['urls'].append(hashlib.md5(url.encode()).hexdigest())
    db['urls'].append(hashlib.md5(title.encode()).hexdigest())
    save_db(db)

# ================== 1. ПОИСК НОВОСТЕЙ ==================
def search_news():
    """Ищет самые свежие новости по AI за последние 6 часов."""
    print("🔍 Поиск свежих AI-новостей...")
    url = "https://newsapi.org/v2/everything"
    params = {
        'q': 'artificial intelligence OR AI OR нейросети OR GPT OR Claude OR Gemini',
        'from': (datetime.now() - timedelta(hours=6)).strftime('%Y-%m-%dT%H:%M:%S'),
        'sortBy': 'publishedAt',
        'language': 'en',
        'pageSize': 15,
        'apiKey': NEWS_API_KEY
    }
    try:
        response = requests.get(url, params=params, timeout=15)
        if response.status_code == 200:
            articles = response.json().get('articles', [])
            print(f"   ✅ Найдено {len(articles)} сырых результатов.")
            return articles
        else:
            print(f"   ❌ Ошибка NewsAPI: {response.status_code}")
            return []
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return []

# ================== 2. ПАРСИНГ ПОЛНОГО ТЕКСТА ==================
def get_full_article_text(url):
    """Извлекает ПОЛНЫЙ текст статьи из URL."""
    print(f"      📖 Парсинг полного текста...")
    try:
        article = Article(url)
        article.download()
        article.parse()
        full_text = article.text
        if full_text and len(full_text) > 500:
            print(f"      ✅ Текст получен ({len(full_text)} символов).")
            return full_text
        else:
            print(f"      ⚠️ Не удалось получить полный текст (мало символов).")
            return None
    except Exception as e:
        print(f"      ❌ Ошибка парсинга: {e}")
        return None

# ================== 3. ПЕРЕВОД НА РУССКИЙ ==================
def translate_to_russian(text):
    """Переводит текст на художественный русский через бесплатный API."""
    if not text:
        return ""
    if re.search('[а-яА-Я]', text):
        return text
    
    # print("      🌍 Перевод на русский...")  # Можно раскомментировать для отладки
    try:
        url = "https://api.mymemory.translated.net/get"
        params = {
            'q': text[:1000],  # Переводим по частям, чтобы не перегружать API
            'langpair': 'en|ru',
            'de': 'your_email@gmail.com'
        }
        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            translated = response.json().get('responseData', {}).get('translatedText', text)
            # Убираем мусорные теги, которые иногда добавляет API
            translated = re.sub(r'\[[^\]]+\]', '', translated)
            return translated
    except Exception as e:
        print(f"      ⚠️ Ошибка перевода: {e}")
    return text

# ================== 4. HUMANIZER (твой скилл) ==================
class Humanizer:
    """
    Твой скилл humanizer. 
    Убирает признаки AI-текста: шаблонные фразы, переспросы, общие слова.
    """
    @staticmethod
    def humanize(text):
        if not text:
            return ""
        
        # 1. Убираем частые AI-шаблоны
        patterns_to_remove = [
            (r'В современном быстро меняющемся мире\s*', ''),
            (r'Стоит отметить, что\s*', ''),
            (r'Важно подчеркнуть,\s*', ''),
            (r'Как уже отмечалось ранее,\s*', ''),
            (r'Нельзя не заметить,\s*', ''),
            (r'Очевидно, что\s*', ''),
            (r'Безусловно,\s*', ''),
            (r'Таким образом,\s*', ''),
            (r'Кроме того,\s*', ''),
            (r'Более того,\s*', ''),
            (r'В заключение\s*', ''),
            (r'Я надеюсь, это поможет!', ''),
            (r'Дайте мне знать, если я могу чем-то еще помочь!', ''),
            (r'Это отличный вопрос!', ''),
            (r'Вы абсолютно правы!', ''),
            (r'Конечно!', ''),
            (r'Пожалуйста!', ''),
        ]
        for pattern, repl in patterns_to_remove:
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        
        # 2. Заменяем общие AI-слова
        word_replacements = {
            r'ключевой': 'важный',
            r'является важным': 'важен',
            r'представляет собой': 'это',
            r'взаимодействие': 'связь',
            r'позволяет': 'дает',
            r'использовать': 'применять',
            r'значительный': 'большой',
            r'улучшение': 'рост',
            r'оптимизация': 'настройка',
            r'функционал': 'возможности',
            r'продукт': 'решение',
            r'пользователь': 'клиент',
        }
        for pattern, repl in word_replacements.items():
            text = re.sub(rf'\b{pattern}\b', repl, text, flags=re.IGNORECASE)
        
        # 3. Убираем множественные восклицания и эмодзи-спам
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'(🔥\s*){2,}', '🔥 ', text)
        
        # 4. Приводим к читаемому виду
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

# ================== 5. ФОРМИРОВАНИЕ ПОСТА ==================
def create_post(article_data):
    """Собирает красивый пост из заголовка, переведенного и хьюманизированного текста."""
    title = article_data['title']
    full_text = article_data['full_text']
    source = article_data['source']
    
    # Переводим заголовок
    title_ru = translate_to_russian(title)
    
    # Переводим и хьюманизируем основной текст
    translated_text = translate_to_russian(full_text)
    humanized_text = Humanizer.humanize(translated_text)
    
    # Ограничиваем длину для Telegram (максимум 4000 символов)
    if len(humanized_text) > 3500:
        humanized_text = humanized_text[:3497] + "..."
    
    post = f"""⚡️ **{title_ru}**

📅 Источник: {source}

---

{humanized_text}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Технологии"""
    
    return post

# ================== 6. ПУБЛИКАЦИЯ ==================
def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        if r.status_code == 200:
            print("   ✅ Пост опубликован!")
            return True
        else:
            print(f"   ❌ Ошибка Telegram: {r.text}")
            return False
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        return False

# ================== ГЛАВНЫЙ ЦИКЛ ==================
def main():
    print("="*70)
    print("🤖 ULTIMATE AI НОВОСТНОЙ АГЕНТ ЗАПУЩЕН")
    print("⚙️  Режим: 1 новость в час | Полный цикл: сбор -> парсинг -> перевод -> humanizer -> пост")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*70)
    
    while True:
        print("\n🔄 Начинаю новый цикл...")
        
        # 1. Ищем свежие новости
        raw_articles = search_news()
        
        if not raw_articles:
            print("⏳ Нет новостей. Жду 30 минут...")
            time.sleep(30 * 60)
            continue
        
        # 2. Обрабатываем каждую новость, пока не найдем новую
        posted = False
        for raw_article in raw_articles:
            title = raw_article.get('title')
            url = raw_article.get('url')
            source = raw_article.get('source', {}).get('name', 'Unknown')
            
            if not title or not url:
                continue
            
            # Проверяем, не публиковали ли мы это уже
            if is_duplicate(url, title):
                print(f"   ⏭️ Пропускаем дубликат: {title[:50]}...")
                continue
            
            print(f"\n📰 Обрабатываю: {title[:60]}...")
            
            # 3. Парсим полный текст
            full_text = get_full_article_text(url)
            if not full_text:
                print("   ⏭️ Пропускаем (не удалось получить полный текст).")
                continue
            
            # 4. Создаем пост
            article_data = {
                'title': title,
                'full_text': full_text,
                'source': source,
                'url': url
            }
            final_post = create_post(article_data)
            
            # 5. Публикуем
            if send_to_telegram(final_post):
                mark_published(url, title)
                posted = True
                break  # Опубликовали одну новость, выходим из цикла
            else:
                print("   ⏭️ Пропускаем (ошибка публикации).")
        
        if not posted:
            print("⏳ Не найдено новых пригодных новостей. Жду 30 минут...")
            time.sleep(30 * 60)
        else:
            print("\n💤 Успешно опубликовано! Жду 1 час до следующей публикации...")
            time.sleep(60 * 60)  # Ждем ровно час

if __name__ == "__main__":
    main()
