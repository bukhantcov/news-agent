import requests
import json
import time
import os
import hashlib
import re
import random
from datetime import datetime, timedelta

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
NEWS_API_KEY = "e08eafb22acc4ad983888ecbcdb492d4"

# Ключевые слова для фильтрации
REAL_AI_KEYWORDS = [
    'openai', 'google ai', 'deepmind', 'anthropic', 'meta ai', 'microsoft ai',
    'gpt', 'claude', 'gemini', 'llama', 'mistral', 'midjourney', 'dalle',
    'нейросеть', 'нейросети', 'искусственный интеллект',
    'ai model', 'llm', 'large language', 'foundation model',
    'sora', 'runway', 'pika', 'stable diffusion'
]

ACTION_KEYWORDS = [
    'released', 'launched', 'announced', 'introduced', 'unveiled', 'presented',
    'выпустил', 'анонсировал', 'представил', 'запустил', 'открыл',
    'update', 'upgrade', 'new version', 'обновил', 'новая версия',
    'available', 'доступен', 'open source', 'opensource'
]

# ============================================================
# ПЕРЕВОДЧИК
# ============================================================
class Translator:
    def __init__(self):
        self.cache = {}
    
    def translate(self, text):
        if not text:
            return text
        
        # Проверяем, есть ли русские буквы
        if re.search(r'[а-яА-Я]', text):
            return text
        
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]
        
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text[:500],
                'langpair': 'en|ru',
                'de': 'denisbuhancov@gmail.com'
            }
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
# HUMANIZER (рерайт человеческим языком)
# ============================================================
class Humanizer:
    @staticmethod
    def rewrite(title, description):
        """Переписываем новость человеческим языком"""
        
        # Убираем шаблонные фразы
        description = re.sub(r'according to sources?|as reported by|in a blog post', '', description, flags=re.IGNORECASE)
        description = re.sub(r'согласно источникам|как сообщает|в блоге', '', description, flags=re.IGNORECASE)
        
        # Живые вступления
        intros = [
            "Свежая новость из мира AI: ",
            "Обратите внимание: ",
            "Только что стало известно: ",
            "Компания анонсировала: ",
            "Вышло важное обновление: "
        ]
        
        # Извлекаем суть (первые 2 предложения)
        sentences = re.split(r'[.!?]+', description)
        core = []
        for s in sentences[:2]:
            s = s.strip()
            if len(s) > 30:
                core.append(s)
        
        essence = '. '.join(core)
        
        if len(essence) > 300:
            essence = essence[:297] + "..."
        
        # Добавляем живое начало
        result = random.choice(intros) + essence[0].lower() + essence[1:] if essence else description
        
        # Добавляем эмоциональную окраску
        emotions = [
            " Это действительно важный шаг!",
            " Технологии развиваются стремительно!",
            " Интересное развитие событий!",
            " Следим за развитием технологии!"
        ]
        
        if len(result) < 400:
            result += random.choice(emotions)
        
        return result

# ============================================================
# ОСНОВНАЯ ЛОГИКА
# ============================================================
class NewsDB:
    def __init__(self):
        self.file = "full_published.json"
        self.load()
    
    def load(self):
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

def is_real_ai_news(article):
    title = article.get('title', '').lower()
    description = article.get('description', '').lower()
    
    # Проверка на ключевые слова AI
    has_ai = any(kw in title for kw in REAL_AI_KEYWORDS)
    if not has_ai:
        has_ai = any(kw in description for kw in REAL_AI_KEYWORDS)
    
    if not has_ai:
        return False, "Нет ключевых слов AI"
    
    # Проверка на действие
    has_action = any(kw in title + description for kw in ACTION_KEYWORDS)
    if not has_action:
        return False, "Нет действия (релиз/анонс)"
    
    # Исключаем увольнения
    if 'layoff' in title or 'увольнени' in title:
        return False, "Новость про увольнения"
    
    return True, "OK"

def get_news():
    """Получение новостей"""
    queries = [
        '("openai" OR "google ai" OR "deepmind")',
        '("gpt" OR "claude" OR "gemini" OR "llama")',
        '("ai model" OR "llm" OR "large language model")',
        '("нейросеть" AND "выпустил") OR "искусственный интеллект"'
    ]
    
    all_articles = []
    
    for query in queries:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'language': 'en,ru',
            'sortBy': 'publishedAt',
            'pageSize': 8,
            'apiKey': NEWS_API_KEY
        }
        
        try:
            response = requests.get(url, params=params, timeout=30)
            data = response.json()
            if data.get('status') == 'ok':
                articles = data.get('articles', [])
                all_articles.extend(articles)
        except:
            pass
        time.sleep(1)
    
    # Удаляем дубликаты
    unique = {}
    for article in all_articles:
        url = article.get('url', '')
        if url and url not in unique:
            unique[url] = article
    
    return list(unique.values())

def send_to_telegram(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
        return r.status_code == 200
    except:
        return False

def create_post(article, translator, humanizer):
    """Создание поста с переводом и рерайтом"""
    
    title = article.get('title', '')
    description = article.get('description', '')
    source = article.get('source', {}).get('name', 'Unknown')
    url_article = article.get('url', '')
    
    # 1. Переводим на русский
    title_ru = translator.translate(title)
    
    # 2. Делаем человеческий рерайт
    if description and len(description) > 50:
        humanized = humanizer.rewrite(title_ru, description)
    else:
        humanized = translator.translate(title)
    
    # 3. Форматируем пост
    post = f"""⚡️ **{title_ru[:80]}**

📅 Источник: {source}

---

{humanized[:600]}

---

🔗 Подробнее: {url_article}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AI #Новости #Нейросети"""
    
    return post

def main():
    print("="*60)
    print("🤖 ПОЛНЫЙ AI НОВОСТНОЙ АГЕНТ")
    print("✅ Перевод на русский")
    print("✅ Humanizer (рерайт)")
    print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
    print("="*60)
    
    translator = Translator()
    humanizer = Humanizer()
    db = NewsDB()
    
    print("\n🔍 Поиск новостей...")
    articles = get_news()
    
    if not articles:
        print("\n❌ Новостей не найдено")
        return
    
    print(f"\n📊 Всего найдено: {len(articles)}")
    
    # Фильтруем
    valid_articles = []
    for article in articles:
        is_valid, reason = is_real_ai_news(article)
        if is_valid and not db.is_published(article.get('url', '')):
            valid_articles.append(article)
            print(f"   ✅ {article.get('title', '')[:50]}...")
        else:
            print(f"   ⏭️ {reason}: {article.get('title', '')[:40]}...")
    
    if not valid_articles:
        print("\n❌ Нет новостей, соответствующих критериям")
        return
    
    # Публикуем первую
    article = valid_articles[0]
    print(f"\n📰 Публикуем:")
    print(f"   {article.get('title', '')[:60]}...")
    
    post = create_post(article, translator, humanizer)
    
    if post and send_to_telegram(post):
        db.mark_published(article.get('url', ''))
        print("\n✅ ОПУБЛИКОВАНО!")
        print("\n📝 Пример перевода и рерайта:")
        print("-"*40)
        print(post[:400] + "...")
    else:
        print("\n❌ Ошибка публикации")

if __name__ == "__main__":
    main()
