import requests
import re
import json
import time
import os
import glob
import hashlib
from datetime import datetime
from pathlib import Path

BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class SmartHumanizer:
    """Умная хьюманизация текста"""
    
    @staticmethod
    def remove_ai_patterns(text):
        """Удаление AI-паттернов"""
        if not text:
            return ""
        
        # Убираем множественные эмодзи
        text = re.sub(r'(🔥\s*){2,}', '🔥 ', text)
        text = re.sub(r'(⚡️\s*){2,}', '⚡️ ', text)
        text = re.sub(r'(💥\s*){2,}', '💥 ', text)
        
        # Убираем дублирование "НОВОСТЬ"
        text = re.sub(r'(НОВОСТЬ\s*){2,}', '🔥 НОВОСТЬ\n\n', text, flags=re.IGNORECASE)
        
        # Убираем шаблонные фразы
        template_phrases = [
            r'В заключени[еи][^.]*\.',
            r'Подводя итог[^.]*\.',
            r'Как уже отмечалось[^.]*\.',
            r'Стоит отметить, что\s*',
            r'Важно подчеркнуть, что\s*',
            r'Очевидно, что\s*',
            r'Безусловно,\s*',
            r'В современном мире\s*',
            r'Нельзя не отметить,\s*',
            r'Следует заметить,\s*',
        ]
        
        for pattern in template_phrases:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Убираем AI-слова
        ai_words = {
            'Additionally': 'Кроме того',
            'Furthermore': 'Более того',
            'Moreover': 'Более того',
            'However': 'Однако',
            'Therefore': 'Поэтому',
            'Thus': 'Так',
            'crucial': 'важный',
            'pivotal': 'ключевой',
            'vibrant': 'активный',
            'landscape': 'среда',
            'showcase': 'показывают',
            'underscore': 'подчеркивают',
            'testament': 'пример',
        }
        
        for ai_word, human_word in ai_words.items():
            text = re.sub(rf'\b{ai_word}\b', human_word, text, flags=re.IGNORECASE)
        
        # Убираем упоминания авторов
        text = re.sub(r'@\w+|Автор:?\s*\w+|от\s+@\w+', '', text)
        
        # Чистим лишние переносы
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    @staticmethod
    def extract_title(text):
        """Извлечение заголовка из текста (статический метод)"""
        if not text:
            return None
        
        lines = text.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 15 and len(line) < 150:
                # Убираем эмодзи в начале
                clean_line = re.sub(r'^[🔥⚡️💥✨🎯📢]+', '', line).strip()
                # Убираем маркдаун
                clean_line = re.sub(r'^\*+', '', clean_line)
                if clean_line and not clean_line.startswith('http'):
                    return clean_line[:100]
        return None
    
    @staticmethod
    def is_quality_news(text):
        """Проверка: новость или личная история"""
        if not text:
            return False
        
        # ❌ Пропускаем личные истории
        bad_patterns = [
            r'я\s+выпустил', r'мой\s+опыт', r'моя\s+история',
            r'скачивания', r'конверсия', r'баги', r'исправил',
            r'я\s+сделал', r'мне\s+написали', r'письма\s+с\s+описанием',
            r'месяц\s+назад\s+я', r'когда\s+я\s+публиковал'
        ]
        
        for pattern in bad_patterns:
            if re.search(pattern, text.lower()):
                return False
        
        # ✅ Хорошие паттерны
        good_patterns = [
            r'выпустил\s+новую\s+версию', r'анонсировал', r'представил',
            r'запустил', r'открыл', r'вышла', r'релиз', r'презентовал',
            r'компания\s+\w+\s+(выпустила|представила|анонсировала)'
        ]
        
        for pattern in good_patterns:
            if re.search(pattern, text.lower()):
                return True
        
        return False


class UniquePoster:
    """Уникальный постинг без дублей"""
    
    def __init__(self):
        self.db_file = "posted_news_db.json"
        self.load_db()
    
    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {
                'posted_hashes': [],
                'posted_titles': [],
                'history': []
            }
    
    def save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, ensure_ascii=False, indent=2)
    
    def get_content_hash(self, text):
        if not text:
            return None
        normalized = re.sub(r'\s+', ' ', text[:300].lower())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def extract_url(self, text):
        urls = re.findall(r'https?://[^\s]+', text)
        return urls[0] if urls else None
    
    def is_duplicate(self, text):
        if not text:
            return False, None
        
        content_hash = self.get_content_hash(text)
        if content_hash and content_hash in self.db['posted_hashes']:
            return True, "hash"
        
        title = SmartHumanizer.extract_title(text)
        if title and title in self.db['posted_titles']:
            return True, "title"
        
        return False, None
    
    def mark_as_posted(self, text, file_path=None):
        if not text:
            return
        
        content_hash = self.get_content_hash(text)
        title = SmartHumanizer.extract_title(text)
        
        if content_hash:
            self.db['posted_hashes'].append(content_hash)
        if title:
            self.db['posted_titles'].append(title)
        
        self.db['history'].append({
            'timestamp': datetime.now().isoformat(),
            'title': title,
            'hash': content_hash,
            'file': file_path
        })
        
        # Ограничиваем размер
        if len(self.db['posted_hashes']) > 1000:
            self.db['posted_hashes'] = self.db['posted_hashes'][-1000:]
        if len(self.db['posted_titles']) > 1000:
            self.db['posted_titles'] = self.db['posted_titles'][-1000:]
        
        self.save_db()


class UniqueFormatPoster:
    """Уникальный формат постов"""
    
    FORMATS = [
        {'header': '🤖 **СВЕЖАЯ НОВОСТЬ** 🤖', 'separator': '▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️'},
        {'header': '📢 **НОВОСТЬ ЧАСА** 📢', 'separator': '▪️▪️▪️▪️▪️▪️▪️▪️▪️▪️'},
        {'header': '⚡️ **В ЭТОТ ЧАС** ⚡️', 'separator': '─━─━─━─━─━─━─'},
        {'header': '🔥 **ТОЛЬКО ЧТО** 🔥', 'separator': '• • • • • • • • • •'},
        {'header': '📰 **НОВОСТЬ** 📰', 'separator': '━━━━━━━━━━━━━━━━━━'},
    ]
    
    def __init__(self):
        self.format_index = 0
    
    def get_next_format(self):
        fmt = self.FORMATS[self.format_index]
        self.format_index = (self.format_index + 1) % len(self.FORMATS)
        return fmt
    
    def create_unique_post(self, content):
        if not content:
            return None
        
        humanized = SmartHumanizer.remove_ai_patterns(content)
        
        if len(humanized) > 1800:
            humanized = humanized[:1797] + "..."
        
        fmt = self.get_next_format()
        
        title = SmartHumanizer.extract_title(content)
        if not title or len(title) < 10:
            title = "Новости искусственного интеллекта"
        
        title = re.sub(r'^[🔥⚡️💥✨🎯📢]+', '', title).strip()
        
        post = f"""{fmt['header']}

**{title}**

{humanized}

{fmt['separator']}

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
🏷 #AIновости #Нейросети"""
        
        return post


class HourlySmartPoster:
    def __init__(self):
        self.formatter = UniqueFormatPoster()
        self.db = UniquePoster()
    
    def find_best_news(self):
        news_files = []
        patterns = [
            "real_news_*/post_*.txt",
            "news_summary_*/telegram/*.txt",
            "full_news_*/telegram/*.txt",
            "*.txt"
        ]
        
        for pattern in patterns:
            found = glob.glob(pattern)
            found = [f for f in found if not os.path.basename(f).startswith('posted_')]
            news_files.extend(found)
        
        news_files.sort(key=os.path.getctime, reverse=True)
        
        best_file = None
        best_score = -1
        
        for file_path in news_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if not SmartHumanizer.is_quality_news(content):
                    continue
                
                is_dup, dup_type = self.db.is_duplicate(content)
                if is_dup:
                    continue
                
                score = min(len(content) / 500, 5)
                
                if any(c in content.lower() for c in ['openai', 'google', 'microsoft']):
                    score += 3
                
                if score > best_score:
                    best_score = score
                    best_file = file_path
                    
            except Exception as e:
                continue
        
        return best_file, best_score
    
    def post_one_news(self):
        print(f"\n🔍 Поиск новой уникальной новости...")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        best_file, score = self.find_best_news()
        
        if not best_file:
            print("❌ Нет новых качественных новостей")
            return False
        
        print(f"📰 Найдено: {os.path.basename(best_file)} (оценка: {score:.1f})")
        
        try:
            with open(best_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            post = self.formatter.create_unique_post(content)
            
            if not post:
                print("❌ Не удалось создать пост")
                return False
            
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': CHANNEL_ID,
                'text': post,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                self.db.mark_as_posted(content, best_file)
                print(f"✅ Опубликовано в {datetime.now().strftime('%H:%M')}")
                return True
            else:
                print(f"❌ Ошибка: {response.text[:200]}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def run_hourly(self):
        print("="*60)
        print("⏰ УМНЫЙ ПОСТИНГ: 1 НОВОСТЬ В ЧАС")
        print("="*60)
        print(f"📢 Канал: {CHANNEL_ID}")
        print("✅ Без дублей")
        print("✅ Уникальное оформление")
        print("="*60)
        
        while True:
            success = self.post_one_news()
            
            if not success:
                print("⏳ Нет новостей, ждем 30 минут...")
                time.sleep(1800)
                continue
            
            print(f"\n⏳ Следующая публикация через 1 час")
            for _ in range(360):
                time.sleep(10)
    
    def run_once(self):
        self.post_one_news()


if __name__ == "__main__":
    import sys
    poster = HourlySmartPoster()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--hourly':
        poster.run_hourly()
    else:
        poster.run_once()
