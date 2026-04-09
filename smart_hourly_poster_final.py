import requests
import re
import json
import time
import os
import glob
import hashlib
from datetime import datetime

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class SmartHumanizer:
    @staticmethod
    def clean_text(text):
        if not text:
            return ""
        
        # Убираем множественные эмодзи
        text = re.sub(r'(🔥\s*){2,}', '🔥 ', text)
        text = re.sub(r'(⚡️\s*){2,}', '⚡️ ', text)
        
        # Убираем дублирование
        text = re.sub(r'(НОВОСТЬ\s*){2,}', 'НОВОСТЬ\n\n', text, flags=re.IGNORECASE)
        
        # Убираем шаблонные фразы
        for pattern in [r'В заключени[еи][^.]*\.', r'Подводя итог[^.]*\.', r'Стоит отметить, что\s*']:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Убираем упоминания авторов
        text = re.sub(r'@\w+|Автор:?\s*\w+', '', text)
        
        # Чистим переносы
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    @staticmethod
    def extract_title(text):
        if not text:
            return "Новости AI"
        
        lines = text.split('\n')
        for line in lines[:10]:
            line = line.strip()
            clean_line = re.sub(r'^[🔥⚡️💥✨🎯📢*_#]+', '', line)
            if len(clean_line) > 15 and len(clean_line) < 100:
                return clean_line.strip()
        
        return "Новости искусственного интеллекта"
    
    @staticmethod
    def is_quality_news(text):
        if not text:
            return False
        
        bad = [r'я\s+выпустил', r'мой\s+опыт', r'скачивания', r'баги', r'исправил']
        for p in bad:
            if re.search(p, text.lower()):
                return False
        
        good = [r'выпустил\s+новую', r'анонсировал', r'представил', r'запустил', r'вышла', r'релиз']
        for p in good:
            if re.search(p, text.lower()):
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
            ("📰", "НОВОСТЬ", "━"),
        ]
        fmt = formats[self.format_index % len(formats)]
        self.format_index += 1
        return fmt
    
    def send_message(self, text):
        """Отправка сообщения - самый простой способ без parse_mode"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        # Отправляем как обычный текст, без какой-либо разметки
        payload = {
            'chat_id': CHANNEL_ID,
            'text': text
            # НЕ добавляем parse_mode - это вызывает ошибку
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                return True
            else:
                error_text = response.text[:200]
                print(f"   Ошибка: {error_text}")
                return False
        except Exception as e:
            print(f"   Ошибка: {e}")
            return False
    
    def find_best_news(self):
        news_files = []
        for pattern in ["real_news_*/post_*.txt", "news_summary_*/telegram/*.txt", "*.txt"]:
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
            except:
                continue
        
        return None, None
    
    def create_post(self, content):
        if not content:
            return None
        
        clean_content = SmartHumanizer.clean_text(content)
        
        if len(clean_content) > 1800:
            clean_content = clean_content[:1797] + "..."
        
        emoji, title_text, separator = self.get_format()
        news_title = SmartHumanizer.extract_title(content)
        
        # Простой текст без Markdown
        post = f"""{emoji} {title_text} {emoji}

{news_title}

{clean_content}

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
