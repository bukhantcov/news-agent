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

class SmartHumanizer:
    """Умная хьюманизация текста"""
    
    @staticmethod
    def clean_text(text):
        """Очистка текста от проблемных символов для Telegram"""
        if not text:
            return ""
        
        # Убираем Markdown символы которые могут сломать парсинг
        text = re.sub(r'[_*[\]()~`>#+\-=|{}.!]', '', text)
        
        # Убираем множественные эмодзи
        text = re.sub(r'(🔥\s*){2,}', '🔥 ', text)
        text = re.sub(r'(⚡️\s*){2,}', '⚡️ ', text)
        
        # Убираем дублирование "НОВОСТЬ"
        text = re.sub(r'(НОВОСТЬ\s*){2,}', 'НОВОСТЬ\n\n', text, flags=re.IGNORECASE)
        
        # Убираем шаблонные фразы
        template_phrases = [
            r'В заключени[еи][^.]*\.',
            r'Подводя итог[^.]*\.',
            r'Стоит отметить, что\s*',
            r'Важно подчеркнуть, что\s*',
            r'Очевидно, что\s*',
        ]
        
        for pattern in template_phrases:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Убираем упоминания авторов
        text = re.sub(r'@\w+|Автор:?\s*\w+', '', text)
        
        # Чистим лишние переносы
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    @staticmethod
    def extract_title(text):
        """Извлечение заголовка"""
        if not text:
            return "Новости AI"
        
        lines = text.split('\n')
        for line in lines[:10]:
            line = line.strip()
            # Убираем эмодзи и спецсимволы
            clean_line = re.sub(r'^[🔥⚡️💥✨🎯📢*_#]+', '', line)
            clean_line = re.sub(r'[\[\({\<].*[\]\)}\>]', '', clean_line)
            if len(clean_line) > 15 and len(clean_line) < 100:
                return clean_line.strip()
        
        return "Новости искусственного интеллекта"
    
    @staticmethod
    def is_quality_news(text):
        """Проверка: новость или нет"""
        if not text:
            return False
        
        bad_patterns = [
            r'я\s+выпустил', r'мой\s+опыт', r'скачивания',
            r'баги', r'исправил', r'я\s+сделал'
        ]
        
        for pattern in bad_patterns:
            if re.search(pattern, text.lower()):
                return False
        
        good_patterns = [
            r'выпустил\s+новую\s+версию', r'анонсировал', r'представил',
            r'запустил', r'открыл', r'вышла', r'релиз'
        ]
        
        for pattern in good_patterns:
            if re.search(pattern, text.lower()):
                return True
        
        return False


class UniquePoster:
    def __init__(self):
        self.db_file = "posted_news_db.json"
        self.load_db()
    
    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'posted_hashes': [], 'posted_titles': []}
    
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
        if h and h in self.db['posted_hashes']:
            return True
        
        title = SmartHumanizer.extract_title(text)
        if title and title in self.db['posted_titles']:
            return True
        
        return False
    
    def mark_posted(self, text):
        if not text:
            return
        
        h = self.get_hash(text)
        if h:
            self.db['posted_hashes'].append(h)
        
        title = SmartHumanizer.extract_title(text)
        if title:
            self.db['posted_titles'].append(title)
        
        if len(self.db['posted_hashes']) > 500:
            self.db['posted_hashes'] = self.db['posted_hashes'][-500:]
        if len(self.db['posted_titles']) > 500:
            self.db['posted_titles'] = self.db['posted_titles'][-500:]
        
        self.save_db()


class HourlyPoster:
    def __init__(self):
        self.db = UniquePoster()
        self.format_index = 0
    
    def get_format(self):
        """Циклическое получение формата"""
        formats = [
            ("🤖", "СВЕЖАЯ НОВОСТЬ", "▫️"),
            ("📢", "НОВОСТЬ ЧАСА", "▪️"),
            ("⚡️", "В ЭТОТ ЧАС", "─"),
            ("🔥", "ТОЛЬКО ЧТО", "•"),
            ("📰", "НОВОСТЬ", "━"),
        ]
        fmt = formats[self.format_index % len(formats)]
        self.format_index += 1
        return fmt
    
    def send_message(self, text):
        """Отправка сообщения (без Markdown)"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        payload = {
            'chat_id': CHANNEL_ID,
            'text': text,
            'parse_mode': None,  # Без Markdown чтобы не было ошибок
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return True
            else:
                print(f"   Ошибка: {response.text[:100]}")
                return False
        except Exception as e:
            print(f"   Ошибка: {e}")
            return False
    
    def find_best_news(self):
        """Поиск лучшей новости"""
        news_files = []
        patterns = ["real_news_*/post_*.txt", "news_summary_*/telegram/*.txt", "*.txt"]
        
        for pattern in patterns:
            found = glob.glob(pattern)
            found = [f for f in found if not os.path.basename(f).startswith('posted_')]
            news_files.extend(found)
        
        news_files.sort(key=os.path.getctime, reverse=True)
        
        for file_path in news_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not SmartHumanizer.is_quality_news(content):
                    continue
                
                if self.db.is_duplicate(content):
                    continue
                
                return file_path, content
                    
            except Exception as e:
                continue
        
        return None, None
    
    def create_post(self, content):
        """Создание поста в чистом тексте (без Markdown)"""
        if not content:
            return None
        
        # Очищаем текст
        clean_content = SmartHumanizer.clean_text(content)
        
        # Ограничиваем длину
        if len(clean_content) > 1800:
            clean_content = clean_content[:1797] + "..."
        
        # Получаем формат
        emoji, title_text, separator = self.get_format()
        
        # Извлекаем заголовок
        news_title = SmartHumanizer.extract_title(content)
        
        # Собираем пост
        post = f"""{emoji} {title_text} {emoji}

{news_title}

{clean_content}

{separator * 10}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AIновости #Нейросети"""
        
        return post
    
    def post_one(self):
        """Публикация одной новости"""
        print(f"\n🔍 Поиск новой новости...")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        file_path, content = self.find_best_news()
        
        if not file_path:
            print("❌ Нет новых новостей")
            return False
        
        print(f"📰 Найдено: {os.path.basename(file_path)}")
        
        post = self.create_post(content)
        
        if not post:
            print("❌ Не удалось создать пост")
            return False
        
        print(f"📤 Публикация...")
        
        if self.send_message(post):
            self.db.mark_posted(content)
            print(f"✅ Опубликовано в {datetime.now().strftime('%H:%M')}")
            return True
        else:
            print(f"❌ Ошибка публикации")
            return False
    
    def run_once(self):
        """Разовый запуск"""
        self.post_one()
    
    def run_hourly(self):
        """Запуск каждый час"""
        print("="*60)
        print("⏰ ПОСТИНГ: 1 НОВОСТЬ В ЧАС")
        print("="*60)
        print(f"📢 Канал: {CHANNEL_ID}")
        print("✅ Без дублей")
        print("✅ Уникальное оформление")
        print("="*60)
        
        while True:
            success = self.post_one()
            
            if not success:
                print("⏳ Нет новостей, ждем 30 минут...")
                time.sleep(1800)
                continue
            
            print(f"\n⏳ Следующая публикация через 1 час")
            time.sleep(3600)


if __name__ == "__main__":
    import sys
    poster = HourlyPoster()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--hourly':
        poster.run_hourly()
    else:
        poster.run_once()
