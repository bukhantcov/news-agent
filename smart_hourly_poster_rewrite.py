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

class Rewriter:
    """Класс для рерайта текста (делаем уникальным)"""
    
    @staticmethod
    def rewrite_news(text):
        """Переписываем новость своими словами"""
        if not text:
            return ""
        
        # Убираем исходные ссылки и упоминания источников
        text = re.sub(r'🔗 https?://[^\s]+', '', text)
        text = re.sub(r'Источник:?[^\n]+', '', text)
        text = re.sub(r'Ссылка:?[^\n]+', '', text)
        text = re.sub(r'Подробнее:?[^\n]+', '', text)
        
        # Заменяем шаблонные фразы
        replacements = {
            r'Компания «([^»]+)» представила': r'«\1» анонсировала',
            r'представила обновленную версию': r'выпустила обновление',
            r'релиз решения осуществляет': r'теперь платформа умеет',
            r'теперь пользователям доступен': r'добавили функцию',
            r'Эксперты добавили': r'разработчики внедрили',
            r'Это критически важно для': r'Это особенно пригодится при',
            r'Благодаря новому функционалу': r'С нововведением',
            r'позволяет выявлять': r'находит',
            r'исключая ручную сверку': r'без участия человека',
            r'в 30 раз сокращаются': r'снижают в 30 раз',
            r'до 100 раз ускоряется': r'ускоряют до 100 раз',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text)
        
        # Убираем технические детали (оставляем суть)
        lines = text.split('\n')
        cleaned_lines = []
        skip_patterns = [
            r'входит в реестр',
            r'интегрируется с',
            r'семантической близости',
            r'вычисляемых полей',
        ]
        
        for line in lines:
            skip = False
            for sp in skip_patterns:
                if re.search(sp, line.lower()):
                    skip = True
                    break
            if not skip and len(line.strip()) > 20:
                cleaned_lines.append(line)
        
        text = '\n'.join(cleaned_lines)
        
        # Добавляем живые фразы
        live_intros = [
            "Интересная новость из мира AI: ",
            "Обратите внимание: ",
            "Вот что произошло: ",
            "Коротко о главном: ",
        ]
        
        # Добавляем не всегда, чтобы не было шаблона
        import random
        if len(text) > 200 and random.random() > 0.6:
            text = random.choice(live_intros) + text[0].lower() + text[1:]
        
        return text.strip()
    
    @staticmethod
    def make_short_summary(text):
        """Создание короткой сводки (2-3 предложения)"""
        # Берем первые 2-3 предложения
        sentences = re.split(r'[.!?]+', text)
        summary = '. '.join(sentences[:3]).strip()
        if len(summary) > 400:
            summary = summary[:397] + "..."
        return summary


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
        
        # Убираем упоминания авторов и источников
        text = re.sub(r'@\w+|Автор:?\s*\w+|Источник:?[^\n]+|🔗[^\n]+', '', text)
        
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
        
        # 1. Сначала рерайтим новость (убираем копипаст)
        rewritten = Rewriter.rewrite_news(content)
        
        # 2. Чистим от лишнего
        clean_content = SmartHumanizer.clean_text(rewritten)
        
        # 3. Создаем короткую версию (2-3 предложения)
        short_summary = Rewriter.make_short_summary(clean_content)
        
        if len(short_summary) > 1500:
            short_summary = short_summary[:1497] + "..."
        
        emoji, title_text, separator = self.get_format()
        news_title = SmartHumanizer.extract_title(content)
        
        # Убираем ссылки и источники из заголовка
        news_title = re.sub(r'🔗.*$', '', news_title)
        news_title = re.sub(r'https?://[^\s]+', '', news_title)
        
        # Пост без ссылки на первоисточник
        post = f"""{emoji} {title_text} {emoji}

{news_title}

{short_summary}

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
        print("✅ Уникальный рерайт (без копипаста)")
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
