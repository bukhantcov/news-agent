import requests
import os
import glob
import re
import json
import time
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class CleanTelegramPoster:
    def __init__(self):
        self.history_file = "posted_history_clean.json"
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
    
    def clean_content(self, text):
        """Очистка контента от упоминаний авторов и лишней информации"""
        
        # Удаляем упоминания авторов
        patterns_to_remove = [
            r'Автор:?\s*@?\w+',
            r'Автор:?\s*[\w\s]+',
            r'By\s+[\w\s]+\n',
            r'Written by\s+[\w\s]+',
            r'Published by\s+[\w\s]+',
            r'@\w+\s+пишет',
            r'пост от @\w+',
            r'рассказывает @\w+',
            r'делится @\w+',
            r'от автора\s+@?\w+',
            r'Source:\s*@?\w+',
            r'Источник:\s*@?\w+',
            r'\[@\w+\]',
            r'\(@\w+\)',
            r'Автор канала',
            r'наш канал',
            r'подписывайтесь на наш',
            r'telegram-канал',
            r'Telegram-канал',
            r'наш Telegram',
            r'наш телеграм',
        ]
        
        for pattern in patterns_to_remove:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Убираем лишние переносы
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Убираем эмодзи авторов если есть
        text = re.sub(r'[👤📝✍️🎓👨‍💻👩‍💻]', '', text)
        
        # Убираем фразы с упоминанием других каналов
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            if not re.search(r'(подписывайся|подпишись|@\w+|t\.me|telegram)', line, re.IGNORECASE):
                cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Очищаем от лишних пробелов в начале строк
        text = re.sub(r'^[ \t]+', '', text, flags=re.MULTILINE)
        
        return text.strip()
    
    def format_for_channel(self, raw_text):
        """Форматирование контента для вашего канала"""
        
        # Сначала очищаем
        cleaned = self.clean_content(raw_text)
        
        # Если текст слишком короткий после очистки, берем оригинал без упоминаний
        if len(cleaned) < 100:
            cleaned = re.sub(r'@\w+|Автор:?\s*\w+', '', raw_text)
        
        # Убираем стандартные подписи
        signatures_to_remove = [
            'С уважением,', 'С уважением,', 'Best regards,',
            'Спасибо за внимание', 'Thank you for reading',
            'Оригинал статьи:', 'Original article:',
            'Перевод:', 'Translation by:'
        ]
        
        for sig in signatures_to_remove:
            cleaned = cleaned.replace(sig, '')
        
        # Убираем ссылки на профили (но оставляем ссылки на источники новостей)
        cleaned = re.sub(r'https?://t\.me/\w+', '', cleaned)
        cleaned = re.sub(r'@\w+(?![\/])', '', cleaned)
        
        # Убираем хештеги с упоминанием каналов
        cleaned = re.sub(r'#\w+channel\w*', '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    def create_clean_post(self, news_text, title=None):
        """Создание чистого поста от лица канала"""
        
        # Форматируем
        content = self.format_for_channel(news_text)
        
        # Добавляем единый стиль канала
        header = f"🔥 **НОВОСТЬ** 🔥\n\n"
        
        # Если есть заголовок - выделяем его
        if title and len(title) > 5:
            # Убираем упоминания авторов из заголовка
            title = re.sub(r'(@\w+|Автор:?\s*\w+)', '', title)
            header = f"🔥 **{title.strip()}** 🔥\n\n"
        
        # Единая подпись канала (без упоминаний других)
        footer = f"\n\n---\n📅 {datetime.now().strftime('%d.%m.%Y')}\n@{CHANNEL_ID.replace('@', '')}\n#AIновости #Нейросети"
        
        final_post = header + content + footer
        
        # Контроль длины
        if len(final_post) > 4000:
            final_post = final_post[:3997] + "..."
        
        return final_post
    
    def read_news_file(self, file_path):
        """Чтение и парсинг файла с новостью"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Пробуем извлечь заголовок
            title = None
            lines = content.split('\n')
            for line in lines[:10]:
                line = line.strip()
                if len(line) > 10 and len(line) < 200 and not line.startswith('http'):
                    if any(word in line.lower() for word in ['новость', '🔥', '💥', '⚡️', 'СРОЧНО']):
                        title = line
                        break
            
            # Если заголовок не нашли, берем первую непустую строку
            if not title:
                for line in lines[:5]:
                    if len(line.strip()) > 15:
                        title = line.strip()
                        break
            
            return self.create_clean_post(content, title)
            
        except Exception as e:
            print(f"   Ошибка чтения: {e}")
            return None
    
    def send_message(self, text):
        """Отправка сообщения"""
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        
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
    
    def post_news(self, file_path):
        """Публикация очищенной новости"""
        if file_path in self.history:
            return False
        
        print(f"   📤 Обработка: {os.path.basename(file_path)[:50]}...")
        
        clean_post = self.read_news_file(file_path)
        
        if not clean_post:
            return False
        
        if len(clean_post) < 50:
            print(f"   ⚠️ Слишком коротко, пропускаем")
            return False
        
        if self.send_message(clean_post):
            self.history[file_path] = datetime.now().isoformat()
            self.save_history()
            print(f"   ✅ Опубликовано!")
            return True
        
        return False
    
    def find_news_files(self):
        """Поиск файлов с новостями"""
        files = []
        
        patterns = [
            "real_news_*/post_*.txt",
            "real_news_*/*.txt",
            "news_summary_*/telegram/*.txt",
            "full_news_*/telegram/*.txt",
            "fresh_news_*/telegram/*.txt",
            "*.txt"
        ]
        
        for pattern in patterns:
            found = glob.glob(pattern)
            # Исключаем системные файлы
            found = [f for f in found if not os.path.basename(f).startswith('posted_')]
            files.extend(found)
        
        files.sort(key=os.path.getctime, reverse=True)
        return files
    
    def run(self, limit=5):
        print(f"\n📢 ЧИСТЫЙ ПОСТИНГ В TELEGRAM")
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
                time.sleep(5)
        
        if posted == 0:
            print("📭 Новых новостей нет")
        else:
            print(f"\n✅ Опубликовано {posted} чистых новостей")

if __name__ == "__main__":
    poster = CleanTelegramPoster()
    poster.run()
