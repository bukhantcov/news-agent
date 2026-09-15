import requests
import os
import glob
import re
import json
import time
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class ProfessionalPoster:
    def __init__(self):
        self.history_file = "posted_professional.json"
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
    
    def clean_and_format(self, raw_text):
        """Очистка и профессиональное форматирование"""
        
        # 1. Убираем множественные эмодзи в начале
        text = re.sub(r'^(🔥\s*)+', '🔥 ', raw_text)
        text = re.sub(r'^(⚡️\s*)+', '⚡️ ', text)
        text = re.sub(r'^(💥\s*)+', '💥 ', text)
        
        # 2. Убираем дублирование "НОВОСТЬ"
        text = re.sub(r'(НОВОСТЬ\s*)+', 'НОВОСТЬ', text, flags=re.IGNORECASE)
        
        # 3. Убираем упоминания авторов
        text = re.sub(r'@\w+|Автор:?\s*\w+|от\s+@\w+', '', text)
        
        # 4. Убираем личные истории
        lines = text.split('\n')
        cleaned_lines = []
        skip_next = False
        
        for line in lines:
            # Пропускаем строки с личными местоимениями
            if re.search(r'\b(я|меня|мне|мой|моя|моё|мной|мы|нас|наш)\b', line.lower()):
                continue
            # Пропускаем строки с призывами
            if re.search(r'(подпис|telegram|канал|@\w+|t\.me)', line.lower()):
                continue
            # Пропускаем строки с цифрами скачиваний (личная статистика)
            if re.search(r'\d+\s*(скачивани|загрузок|установок)', line.lower()):
                continue
            cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # 5. Профессиональный формат
        # Один эмодзи в начале, слово НОВОСТЬ один раз
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    def create_professional_post(self, content, title=None):
        """Создание профессионального поста"""
        
        # Очищаем контент
        cleaned = self.clean_and_format(content)
        
        # Если после очистки слишком коротко - пропускаем
        if len(cleaned) < 100:
            return None
        
        # Профессиональный шаблон
        post = f"""🔥 **НОВОСТЬ**

{cleaned[:2000]}

---
📅 {datetime.now().strftime('%d.%m.%Y')}
📌 @DenisBukhancov_CRM_AI

#AI #Нейросети #НовостиAI"""
        
        return post
    
    def send_message(self, text):
        """Отправка сообщения"""
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
        patterns = [
            "real_news_*/post_*.txt",
            "news_summary_*/telegram/*.txt",
            "*.txt"
        ]
        
        for pattern in patterns:
            found = glob.glob(pattern)
            found = [f for f in found if not os.path.basename(f).startswith('posted_')]
            files.extend(found)
        
        files.sort(key=os.path.getctime, reverse=True)
        return files
    
    def post_news(self, file_path):
        """Публикация новости"""
        if file_path in self.history:
            return False
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Проверяем что это не личная история
            bad_patterns = [
                r'я\s+выпустил', r'мой\s+опыт', r'моя\s+история',
                r'скачивания', r'конверсия', r'баги', r'исправил'
            ]
            
            for pattern in bad_patterns:
                if re.search(pattern, content.lower()):
                    print(f"   ⏭️ Личная история, пропускаем")
                    return False
            
            post = self.create_professional_post(content)
            
            if not post:
                return False
            
            print(f"   📤 {os.path.basename(file_path)[:40]}...")
            
            if self.send_message(post):
                self.history[file_path] = datetime.now().isoformat()
                self.save_history()
                print(f"   ✅ Опубликовано!")
                return True
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
        
        return False
    
    def run(self, limit=3):
        print(f"\n📢 ПРОФЕССИОНАЛЬНЫЙ ПОСТИНГ")
        print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("="*50)
        
        news_files = self.find_news_files()
        
        if not news_files:
            print("❌ Файлы с новостями не найдены")
            return
        
        posted = 0
        for file_path in news_files:
            if posted >= limit:
                break
            if self.post_news(file_path):
                posted += 1
                time.sleep(5)
        
        print(f"\n✅ Опубликовано {posted} новостей")

if __name__ == "__main__":
    poster = ProfessionalPoster()
    poster.run()
