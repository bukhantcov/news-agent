import requests
import re
import json
import time
import os
import glob
import hashlib
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class ContentCleaner:
    """Очистка текста от мусора"""
    
    @staticmethod
    def remove_garbage(text):
        """Удаление мусорных символов и обрезанных фрагментов"""
        if not text:
            return ""
        
        # Убираем ...* и подобные обрезания
        text = re.sub(r'\.\.\.\*', '', text)
        text = re.sub(r'\.\.\.\s*\*', '', text)
        text = re.sub(r'\*\.\.\.', '', text)
        text = re.sub(r'\*{2,}', '', text)
        
        # Убираем обрезанные предложения в конце
        text = re.sub(r'\.\.\.\s*$', '', text)
        text = re.sub(r'\.\.\.\s*\n', '\n', text)
        
        # Убираем мусорные фрагменты
        garbage_patterns = [
            r'Ryzen и 16\s*$',
            r'Ryzen и 16 Гбайт[^\n]*\.\.\.',
            r'процент[а-я]*\s*$',
            r'баксов\s*$',
            r'то ли еще браслет[^\n]*$',
            r'то ли уже часы[^\n]*$',
            r'эволюции AMD[^\n]*$',
            r'Обзор HUAWEI[^\n]*$',
            r'Компьютер месяца[^\n]*$',
        ]
        
        for pattern in garbage_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Убираем одиночные звездочки
        text = re.sub(r'\*([^*]+)\*', r'\1', text)
        text = re.sub(r'^\*\s*', '', text, flags=re.MULTILINE)
        text = re.sub(r'\s*\*$', '', text, flags=re.MULTILINE)
        
        return text.strip()


class ContentFilter:
    """Жесткая фильтрация контента"""
    
    # Ключевые слова настоящих новостей
    NEWS_KEYWORDS = [
        'выпустила', 'анонсировала', 'представила', 'запустила', 'открыла',
        'вышла', 'релиз', 'презентовала', 'обновила', 'интегрировала',
        'выпущена', 'доступна', 'запущена', 'анонс',
    ]
    
    # Компании
    COMPANIES = [
        'google', 'openai', 'microsoft', 'meta', 'amazon', 'apple',
        'sber', 'yandex', 'deepmind', 'anthropic', 'nvidia', 'amd'
    ]
    
    # Мусорные паттерны
    GARBAGE_PATTERNS = [
        r'ежедневного письма от Superhuman',
        r'адаптация ежедневного письма',
        r'которую читают более.*миллиона',
        r'дайджест', r'рассылка',
        r'сегодня узнайте о',
        r'популярные посты в соцсетях',
        r'Обзор\s+[\w\s]+:',
        r'Компьютер месяца',
        r'то ли еще браслет',
        r'то ли уже часы',
        r'эволюции AMD',
    ]
    
    @classmethod
    def is_real_news(cls, text):
        """Проверка: настоящая новость или мусор"""
        if not text or len(text) < 150:
            return False
        
        text_lower = text.lower()
        
        # Проверка на мусор
        for pattern in cls.GARBAGE_PATTERNS:
            if re.search(pattern, text_lower):
                print(f"   🚫 Мусор: {pattern}")
                return False
        
        # Должна быть компания
        has_company = any(c in text_lower for c in cls.COMPANIES)
        if not has_company:
            print(f"   🚫 Нет компании")
            return False
        
        # Должен быть новостной глагол
        has_news = any(kw in text_lower for kw in cls.NEWS_KEYWORDS)
        if not has_news:
            print(f"   🚫 Нет новостного глагола")
            return False
        
        return True
    
    @classmethod
    def extract_news_core(cls, text):
        """Извлечение основной новости"""
        lines = text.split('\n')
        news_lines = []
        
        for line in lines:
            # Пропускаем мусорные строки
            if any(p in line.lower() for p in cls.GARBAGE_PATTERNS):
                continue
            # Пропускаем очень короткие строки
            if len(line.strip()) < 30:
                continue
            # Пропускаем строки с датами в начале
            if re.match(r'^\d{2}\.\d{2}\.\d{4}', line):
                continue
            # Пропускаем строки с авторами
            if re.search(r'Павел Котов|Иванов|Петров', line):
                continue
            
            clean_line = ContentCleaner.remove_garbage(line)
            if clean_line and len(clean_line) > 20:
                news_lines.append(clean_line)
        
        result = '\n'.join(news_lines[:5])  # Берем первые 5 строк
        return result.strip()


class Rewriter:
    @staticmethod
    def rewrite_news(text):
        """Переписываем новость человеческим языком"""
        if not text:
            return ""
        
        # Убираем лишние детали
        text = re.sub(r'\d{2}\.\d{2}\.\d{4}', '', text)
        text = re.sub(r'[А-Я][а-я]+\s+[А-Я][а-я]+', '', text)  # Убираем имена
        
        # Оставляем только суть
        sentences = re.split(r'[.!?]+', text)
        core_sentences = []
        
        for sentence in sentences[:4]:  # Первые 4 предложения
            sentence = sentence.strip()
            if len(sentence) > 30 and len(sentence) < 300:
                core_sentences.append(sentence)
        
        result = '. '.join(core_sentences)
        
        if len(result) > 1000:
            result = result[:997] + "..."
        
        return result.strip()


class SmartHumanizer:
    @staticmethod
    def extract_title(text):
        if not text:
            return "Новости AI"
        
        # Ищем первое предложение с компанией
        sentences = re.split(r'[.!?]+', text)
        for sentence in sentences[:3]:
            sentence = sentence.strip()
            if len(sentence) > 20 and len(sentence) < 150:
                # Чистим от мусора
                clean = re.sub(r'[\[\]{}()*]', '', sentence)
                clean = re.sub(r'\d{2}\.\d{2}\.\d{4}', '', clean)
                if clean:
                    return clean[:80]
        
        return "Новости искусственного интеллекта"
    
    @staticmethod
    def clean_text(text):
        if not text:
            return ""
        
        text = ContentCleaner.remove_garbage(text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()


class UniquePoster:
    def __init__(self):
        self.db_file = "posted_news_db.json"
        self.load_db()
    
    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'hashes': [], 'titles': []}
    
    def save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, ensure_ascii=False, indent=2)
    
    def get_hash(self, text):
        if not text:
            return None
        normalized = re.sub(r'\s+', ' ', text[:200].lower())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def is_duplicate(self, text):
        if not text:
            return False
        
        h = self.get_hash(text)
        if h and h in self.db['hashes']:
            return True
        
        title = SmartHumanizer.extract_title(text)
        if title and title in self.db['titles']:
            return True
        
        return False
    
    def mark_posted(self, text):
        if not text:
            return
        
        h = self.get_hash(text)
        if h:
            self.db['hashes'].append(h)
        
        title = SmartHumanizer.extract_title(text)
        if title:
            self.db['titles'].append(title)
        
        if len(self.db['hashes']) > 500:
            self.db['hashes'] = self.db['hashes'][-500:]
        if len(self.db['titles']) > 500:
            self.db['titles'] = self.db['titles'][-500:]
        
        self.save_db()


class HourlyPoster:
    def __init__(self):
        self.db = UniquePoster()
        self.format_index = 0
    
    def get_format(self):
        formats = [
            ("🤖", "СВЕЖАЯ НОВОСТЬ", "▫️"),
            ("📢", "НОВОСТЬ ЧАСА", "▪️"),
            ("⚡️", "В ЭТОТ ЧАС", "─"),
            ("🔥", "ТОЛЬКО ЧТО", "•"),
        ]
        fmt = formats[self.format_index % len(formats)]
        self.format_index += 1
        return fmt
    
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': CHANNEL_ID, 'text': text}
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"   Ошибка: {e}")
            return False
    
    def find_best_news(self):
        news_files = []
        for pattern in ["real_news_*/post_*.txt", "*.txt"]:
            found = glob.glob(pattern)
            found = [f for f in found if not os.path.basename(f).startswith('posted_')]
            news_files.extend(found)
        
        news_files.sort(key=os.path.getctime, reverse=True)
        
        for file_path in news_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Извлекаем чистую новость
                core_news = ContentFilter.extract_news_core(content)
                
                if not ContentFilter.is_real_news(core_news):
                    continue
                
                if len(core_news) < 150:
                    continue
                
                if self.db.is_duplicate(core_news):
                    continue
                
                return file_path, core_news
            except:
                continue
        
        return None, None
    
    def create_post(self, content):
        if not content:
            return None
        
        # Чистим от мусора
        cleaned = ContentCleaner.remove_garbage(content)
        
        # Рерайт
        rewritten = Rewriter.rewrite_news(cleaned)
        
        # Чистка
        final = SmartHumanizer.clean_text(rewritten)
        
        if len(final) > 1000:
            final = final[:997] + "..."
        
        emoji, title_text, separator = self.get_format()
        news_title = SmartHumanizer.extract_title(content)
        
        post = f"""{emoji} {title_text} {emoji}

{news_title}

{final}

{separator * 10}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AIновости #Нейросети"""
        
        return post
    
    def post_one(self):
        print(f"\n🔍 Поиск новой новости...")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        file_path, content = self.find_best_news()
        
        if not file_path:
            print("❌ Нет новых качественных новостей")
            return False
        
        print(f"📰 Найдено: {os.path.basename(file_path)}")
        
        post = self.create_post(content)
        
        if not post or len(post) < 150:
            print("❌ Не удалось создать пост")
            return False
        
        print(f"📤 Публикация...")
        
        if self.send_message(post):
            self.db.mark_posted(content)
            print(f"✅ Опубликовано!")
            return True
        else:
            print(f"❌ Ошибка публикации")
            return False
    
    def run_once(self):
        self.post_one()
    
    def run_hourly(self):
        print("="*50)
        print("⏰ 1 НОВОСТЬ В ЧАС")
        print("="*50)
        print(f"📢 {CHANNEL_ID}")
        print("="*50)
        
        while True:
            success = self.post_one()
            
            if not success:
                print("⏳ Ждем 30 минут...")
                time.sleep(1800)
                continue
            
            print(f"\n⏳ Следующая через 1 час")
            time.sleep(3600)


if __name__ == "__main__":
    import sys
    poster = HourlyPoster()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--hourly':
        poster.run_hourly()
    else:
        poster.run_once()
