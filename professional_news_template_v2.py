import requests
import re
import json
import time
import os
import glob
import hashlib
import random
from datetime import datetime
from pathlib import Path

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class NewsProcessor:
    def __init__(self):
        self.db_file = os.path.join(os.path.dirname(__file__), "posted_news_db.json")
        self.load_db()
    
    def find_news_files(self):
        """Рекурсивный поиск файлов с новостями"""
        current_dir = os.path.dirname(__file__)
        news_files = []
        
        # Паттерны поиска
        patterns = [
            "**/post_*.txt",
            "**/news_*.txt",
            "**/*post*.txt",
            "real_news_*/**/*.txt",
            "news_summary_*/**/*.txt",
            "full_news_*/**/*.txt",
            "*.txt"
        ]
        
        for pattern in patterns:
            found = glob.glob(os.path.join(current_dir, pattern), recursive=True)
            # Фильтруем системные файлы
            found = [f for f in found if not os.path.basename(f).startswith('posted_')]
            found = [f for f in found if not os.path.basename(f).startswith('requirements')]
            found = [f for f in found if 'venv' not in f]
            news_files.extend(found)
        
        # Удаляем дубликаты и сортируем по времени
        news_files = list(set(news_files))
        news_files.sort(key=os.path.getctime, reverse=True)
        
        return news_files
    
    def find_best_news(self):
        """Поиск лучшей непрочитанной новости"""
        news_files = self.find_news_files()
        
        print(f"📁 Найдено файлов: {len(news_files)}")
        
        for file_path in news_files:
            try:
                # Пропускаем слишком маленькие файлы
                if os.path.getsize(file_path) < 300:
                    continue
                
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if len(content) < 300:
                    continue
                
                # Проверка на дубликат
                content_hash = hashlib.md5(content[:200].encode()).hexdigest()
                if content_hash in self.db.get('hashes', []):
                    continue
                
                # Извлекаем заголовок
                lines = content.split('\n')
                title = ""
                for line in lines[:10]:
                    line = line.strip()
                    if len(line) > 15 and len(line) < 150 and not line.startswith('http'):
                        title = line
                        break
                
                if not title:
                    title = content[:80]
                
                return file_path, title, content
                
            except Exception as e:
                continue
        
        return None, None, None
    
    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'hashes': [], 'titles': []}
    
    def save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, ensure_ascii=False, indent=2)
    
    def mark_posted(self, content, title):
        content_hash = hashlib.md5(content[:200].encode()).hexdigest()
        if content_hash not in self.db['hashes']:
            self.db['hashes'].append(content_hash)
        if title and title not in self.db['titles']:
            self.db['titles'].append(title)
        self.save_db()
    
    def create_post(self, title, content):
        """Создание поста"""
        clean_content = re.sub(r'\n+', ' ', content)
        clean_content = re.sub(r'\s+', ' ', clean_content)
        essence = clean_content[:497] + "..." if len(clean_content) > 500 else clean_content
        
        post = f"""⚡️ **{title[:80]}**

---

🧠 **Суть новости**

{essence}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AIновости #Нейросети"""
        
        return post
    
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': CHANNEL_ID, 'text': text}
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False
    
    def post_one(self):
        print(f"\n🔍 Поиск новостей...")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        file_path, title, content = self.find_best_news()
        
        if not file_path:
            print("❌ Нет новых новостей для публикации")
            print("💡 Запустите python3 real_news_agent.py для сбора новостей")
            return False
        
        print(f"📰 Найдено: {os.path.basename(file_path)}")
        print(f"📝 Заголовок: {title[:60]}...")
        
        post = self.create_post(title, content)
        
        if len(post) > 4096:
            post = post[:4093] + "..."
        
        print(f"📤 Публикация ({len(post)} символов)...")
        
        if self.send_message(post):
            self.mark_posted(content, title)
            print(f"✅ Опубликовано!")
            return True
        else:
            print(f"❌ Ошибка публикации")
            return False
    
    def run_once(self):
        self.post_one()


if __name__ == "__main__":
    processor = NewsProcessor()
    processor.run_once()
