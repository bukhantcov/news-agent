import requests
import os
import glob
import time
import json
from datetime import datetime

# КОНФИГУРАЦИЯ
BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class AutoPoster:
    def __init__(self):
        self.history_file = "posted_history.json"
        self.load_history()
    
    def load_history(self):
        if os.path.exists(self.history_file):
            with open(self.history_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = {}
    
    def save_history(self):
        with open(self.history_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
        if len(text) > 4000:
            text = text[:3997] + "..."
        
        payload = {
            'chat_id': CHANNEL_ID,
            'text': text,
            'parse_mode': 'Markdown',
            'disable_web_page_preview': True
        }
        
        try:
            response = requests.post(url, json=payload, timeout=30)
            return response.status_code == 200
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False
    
    def find_news_files(self):
        """Поиск файлов с новостями"""
        files = []
        
        # Ищем во всех возможных папках
        for pattern in [
            "real_news_*/post_*.txt",
            "real_news_*/*.txt", 
            "news_summary_*/telegram/*.txt",
            "full_news_*/telegram/*.txt",
            "fresh_news_*/telegram/*.txt"
        ]:
            files.extend(glob.glob(pattern))
        
        # Сортируем по времени создания (новые первые)
        files.sort(key=os.path.getctime, reverse=True)
        return files
    
    def post_news(self, file_path):
        """Публикация одной новости"""
        if file_path in self.history:
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Ограничиваем длину
            if len(content) > 3500:
                content = content[:3500] + "\n\n... (продолжение в следующем посте)"
            
            print(f"   📤 {os.path.basename(file_path)[:50]}...")
            
            if self.send_message(content):
                self.history[file_path] = datetime.now().isoformat()
                self.save_history()
                return True
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        return False
    
    def run(self, limit=5):
        print(f"\n📢 Публикация новостей в Telegram")
        print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("="*50)
        
        news_files = self.find_news_files()
        
        if not news_files:
            print("❌ Файлы с новостями не найдены")
            return
        
        print(f"📁 Найдено файлов: {len(news_files)}")
        
        posted = 0
        for file_path in news_files:
            if posted >= limit:
                break
            if self.post_news(file_path):
                posted += 1
                time.sleep(3)  # Пауза между постами
        
        if posted == 0:
            print("📭 Новых новостей нет")
        else:
            print(f"\n✅ Опубликовано {posted} новостей")

if __name__ == "__main__":
    poster = AutoPoster()
    poster.run()
