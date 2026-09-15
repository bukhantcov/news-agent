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

# ⚠️ НАСТРОЙКИ КАЧЕСТВА ⚠️
MIN_TEXT_LENGTH = 500      # Минимальная длина текста (символов)
MAX_TEXT_LENGTH = 1800     # Максимальная длина для поста
MIN_NEWS_LENGTH = 400      # Минимальная длина новости после очистки

class QualityFilter:
    """Фильтр качества контента"""
    
    @staticmethod
    def check_length(text, min_len=MIN_TEXT_LENGTH):
        """Проверка длины текста"""
        if not text:
            return False, 0
        
        clean_text = re.sub(r'\s+', ' ', text)
        length = len(clean_text)
        
        if length < min_len:
            print(f"   📏 Слишком коротко: {length} символов (минимум {min_len})")
            return False, length
        
        print(f"   📏 Длина текста: {length} символов ✅")
        return True, length
    
    @staticmethod
    def is_quality_news(text):
        """Комплексная проверка качества новости"""
        if not text:
            return False
        
        # Проверка длины
        is_long_enough, length = QualityFilter.check_length(text)
        if not is_long_enough:
            return False
        
        # Проверка на мусорные паттерны
        garbage_patterns = [
            r'ежедневного письма от Superhuman',
            r'адаптация ежедневного письма',
            r'дайджест', r'рассылка',
            r'сегодня узнайте о',
            r'популярные посты',
            r'Обзор\s+[\w\s]+:',
            r'Компьютер месяца',
            r'то ли еще браслет',
            r'то ли уже часы',
            r'эволюции AMD',
            r'Ryzen и 16',
            r'три процента за двадцать баксов',
        ]
        
        text_lower = text.lower()
        for pattern in garbage_patterns:
            if re.search(pattern, text_lower):
                print(f"   🚫 Мусорный паттерн: {pattern}")
                return False
        
        # Должна быть компания или технология
        companies = [
            'google', 'openai', 'microsoft', 'meta', 'amazon', 'apple',
            'sber', 'yandex', 'deepmind', 'anthropic', 'nvidia', 'amd',
            'норбит', 'норбит', 'ai', 'искусственный интеллект', 'нейросеть'
        ]
        
        has_company = any(c in text_lower for c in companies)
        if not has_company:
            print(f"   🚫 Нет ключевых слов (компания/технология)")
            return False
        
        # Должен быть новостной глагол
        news_words = ['выпустила', 'анонсировала', 'представила', 'запустила', 
                      'открыла', 'вышла', 'релиз', 'презентовала', 'обновила']
        
        has_news = any(kw in text_lower for kw in news_words)
        if not has_news:
            print(f"   🚫 Нет новостного глагола")
            return False
        
        return True


class ContentCleaner:
    """Очистка текста от мусора"""
    
    @staticmethod
    def remove_garbage(text):
        if not text:
            return ""
        
        # Убираем ...* и подобные
        text = re.sub(r'\.\.\.\*', '', text)
        text = re.sub(r'\.\.\.\s*\*', '', text)
        text = re.sub(r'\*\.\.\.', '', text)
        text = re.sub(r'\.\.\.\s*$', '', text)
        
        # Убираем мусорные фрагменты
        garbage_patterns = [
            r'Ryzen и 16\s*$',
            r'Ryzen и 16 Гбайт[^\n]*\.\.\.',
            r'процент[а-я]*\s*$',
            r'баксов\s*$',
            r'\d{2}\.\d{2}\.\d{4}\s*,\s*[А-Я][а-я]+\s+[А-Я][а-я]+',
        ]
        
        for pattern in garbage_patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    @staticmethod
    def extract_core_news(text):
        """Извлечение основной новости"""
        lines = text.split('\n')
        news_lines = []
        
        for line in lines:
            if len(line.strip()) < 30:
                continue
            if re.match(r'^\d{2}\.\d{2}\.\d{4}', line):
                continue
            if re.search(r'Павел Котов|Иванов|Петров|Сидоров', line):
                continue
            
            clean_line = ContentCleaner.remove_garbage(line)
            if clean_line and len(clean_line) > 20:
                news_lines.append(clean_line)
        
        result = ' '.join(news_lines[:8])
        
        # Обрезаем до целого предложения
        if len(result) > MAX_TEXT_LENGTH:
            result = result[:MAX_TEXT_LENGTH]
            last_period = result.rfind('.')
            if last_period > MAX_TEXT_LENGTH - 300:
                result = result[:last_period + 1]
        
        return result.strip()


class Rewriter:
    @staticmethod
    def rewrite_news(text):
        """Переписываем новость человеческим языком"""
        if not text:
            return ""
        
        # Убираем лишние детали
        text = re.sub(r'\d{2}\.\d{2}\.\d{4}', '', text)
        text = re.sub(r'[А-Я][а-я]+\s+[А-Я][а-я]+', '', text)
        
        # Оставляем только суть (первые 4-5 предложений)
        sentences = re.split(r'[.!?]+', text)
        core_sentences = []
        
        for sentence in sentences[:5]:
            sentence = sentence.strip()
            if 30 < len(sentence) < 400:
                core_sentences.append(sentence)
        
        result = '. '.join(core_sentences)
        
        # Добавляем заключительную фразу если нужно
        if len(result) > 100 and not result.endswith('.'):
            result += '.'
        
        return result.strip()


class SmartHumanizer:
    @staticmethod
    def extract_title(text):
        if not text:
            return "Новости AI"
        
        sentences = re.split(r'[.!?]', text)
        for sentence in sentences[:3]:
            sentence = sentence.strip()
            if 20 < len(sentence) < 120:
                clean = re.sub(r'[\[\]{}()*]', '', sentence)
                clean = re.sub(r'\d{2}\.\d{2}\.\d{4}', '', clean)
                if clean and not clean.startswith('Обзор'):
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
            print(f"   🔄 Дубликат по хешу")
            return True
        
        title = SmartHumanizer.extract_title(text)
        if title and title in self.db['titles']:
            print(f"   🔄 Дубликат по заголовку")
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
            print(f"   ❌ Ошибка: {e}")
            return False
    
    def find_best_news(self):
        """Поиск лучшей новости с проверкой длины"""
        news_files = []
        for pattern in ["real_news_*/post_*.txt", "news_*.txt", "*.txt"]:
            found = glob.glob(pattern)
            found = [f for f in found if not os.path.basename(f).startswith('posted_')]
            news_files.extend(found)
        
        news_files.sort(key=os.path.getctime, reverse=True)
        
        for file_path in news_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Извлекаем чистую новость
                core_news = ContentCleaner.extract_core_news(content)
                
                # Проверка качества
                if not QualityFilter.is_quality_news(core_news):
                    continue
                
                # Дополнительная проверка длины
                is_ok, length = QualityFilter.check_length(core_news, MIN_NEWS_LENGTH)
                if not is_ok:
                    continue
                
                if self.db.is_duplicate(core_news):
                    continue
                
                print(f"   ✅ Новость прошла проверку ({length} символов)")
                return file_path, core_news
                
            except Exception as e:
                continue
        
        return None, None
    
    def create_post(self, content):
        if not content:
            return None
        
        # Чистим
        cleaned = ContentCleaner.remove_garbage(content)
        
        # Рерайт
        rewritten = Rewriter.rewrite_news(cleaned)
        
        # Финальная проверка длины
        if len(rewritten) < MIN_TEXT_LENGTH:
            print(f"   ❌ После рерайта слишком коротко: {len(rewritten)} символов")
            return None
        
        # Ограничиваем максимальную длину
        if len(rewritten) > MAX_TEXT_LENGTH:
            rewritten = rewritten[:MAX_TEXT_LENGTH]
            last_period = rewritten.rfind('.')
            if last_period > MAX_TEXT_LENGTH - 300:
                rewritten = rewritten[:last_period + 1]
        
        emoji, title_text, separator = self.get_format()
        news_title = SmartHumanizer.extract_title(content)
        
        post = f"""{emoji} {title_text} {emoji}

{news_title}

{rewritten}

{separator * 10}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AIновости #Нейросети"""
        
        return post
    
    def post_one(self):
        print(f"\n🔍 Поиск новой новости...")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        print(f"📏 Минимальная длина: {MIN_TEXT_LENGTH} символов")
        
        file_path, content = self.find_best_news()
        
        if not file_path:
            print("❌ Нет новостей, соответствующих критериям качества")
            return False
        
        print(f"📰 Найдено: {os.path.basename(file_path)}")
        
        post = self.create_post(content)
        
        if not post or len(post) < 200:
            print("❌ Не удалось создать качественный пост")
            return False
        
        print(f"📤 Публикация ({len(post)} символов)...")
        
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
        print(f"📏 Минимум {MIN_TEXT_LENGTH} символов")
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
