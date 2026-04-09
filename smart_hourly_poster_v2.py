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

class ContentFilter:
    """Жесткая фильтрация контента - только настоящие новости"""
    
    # Ключевые слова настоящих новостей
    NEWS_KEYWORDS = [
        'выпустил', 'анонсировал', 'представил', 'запустил', 'открыл',
        'вышла', 'релиз', 'презентовал', 'обновил', 'интегрировал',
        'выпущена', 'доступна', 'запущена', 'анонс', 'релиз',
        'представлена', 'новая версия', 'обновление'
    ]
    
    # Ключевые слова компаний
    COMPANY_KEYWORDS = [
        'openai', 'google', 'microsoft', 'meta', 'amazon', 'apple',
        'sber', 'yandex', 'tinkoff', 'deepmind', 'anthropic',
        'midjourney', 'stability', 'nvidia', 'intel', 'amd',
        'норбит', 'norbit', 'сбер', 'яндекс'
    ]
    
    # ❌ Плохие паттерны (НЕ новости)
    BAD_PATTERNS = [
        # Рекламные рассылки
        r'ежедневного письма от Superhuman',
        r'адаптация ежедневного письма',
        r'которую читают более.*миллиона человек',
        r'избранное из мира AI',
        r'поехали',
        r'дайджест',
        r'рассылка',
        r'подпишись',
        r'подписывайтесь',
        
        # Личные истории
        r'я\s+выпустил', r'мой\s+опыт', r'моя\s+история',
        r'скачивания', r'конверсия', r'баги', r'исправил',
        r'я\s+сделал', r'мне\s+написали', r'месяц\s+назад',
        
        # Бессмысленный контент
        r'сегодня узнайте о',
        r'как создавать.*с помощью ии',
        r'популярные посты в соцсетях',
        r'давайте разберем',
        r'что такое.*и как',
        
        # Шаблонные фразы
        r'в этом выпуске',
        r'в сегодняшнем дайджесте',
        r'топ.*новостей',
        r'лучшие материалы',
    ]
    
    @classmethod
    def is_real_news(cls, text):
        """Проверка: настоящая новость или мусор"""
        if not text:
            return False
        
        text_lower = text.lower()
        
        # Проверка на плохие паттерны (мусор)
        for pattern in cls.BAD_PATTERNS:
            if re.search(pattern, text_lower):
                print(f"   🚫 Отфильтровано (мусор): {pattern}")
                return False
        
        # Должен быть хотя бы один новостной глагол
        has_news_word = any(kw in text_lower for kw in cls.NEWS_KEYWORDS)
        if not has_news_word:
            print(f"   🚫 Отфильтровано (нет новостных слов)")
            return False
        
        # Должна быть хотя бы одна компания
        has_company = any(company in text_lower for company in cls.COMPANY_KEYWORDS)
        if not has_company:
            print(f"   🚫 Отфильтровано (нет упоминания компаний)")
            return False
        
        # Проверка длины (короткий текст = не новость)
        if len(text) < 200:
            print(f"   🚫 Отфильтровано (слишком коротко)")
            return False
        
        return True
    
    @classmethod
    def extract_real_news(cls, text):
        """Извлечение только новостной части из мусора"""
        lines = text.split('\n')
        news_lines = []
        in_news = True
        
        for line in lines:
            # Стоп-слова для обрезки
            stop_words = ['подпишись', 'дайджест', 'рассылка', 'поехали', 'сегодня узнайте']
            if any(word in line.lower() for word in stop_words):
                in_news = False
                continue
            
            if in_news and len(line.strip()) > 30:
                # Убираем ссылки
                clean_line = re.sub(r'https?://[^\s]+', '', line)
                # Убираем эмодзи
                clean_line = re.sub(r'[🔥⚡️💥✨🎯📢🤖📰]', '', clean_line)
                if clean_line.strip():
                    news_lines.append(clean_line.strip())
        
        return '\n'.join(news_lines)


class Rewriter:
    @staticmethod
    def rewrite_news(text):
        """Переписываем новость своими словами"""
        if not text:
            return ""
        
        # Заменяем шаблонные фразы
        replacements = {
            r'Компания «([^»]+)» представила': r'«\1» анонсировала',
            r'представила новую версию': r'выпустила обновление',
            r'представила новую ИИ-модель': r'анонсировала свежую нейросеть',
            r'релиз решения осуществляет': r'теперь платформа умеет',
            r'теперь пользователям доступен': r'добавили функцию',
            r'Эксперты добавили': r'разработчики внедрили',
            r'Это критически важно для': r'Это особенно пригодится при',
            r'Благодаря новому функционалу': r'С нововведением',
            r'позволяет выявлять': r'находит',
            r'исключая ручную сверку': r'без участия человека',
        }
        
        for pattern, replacement in replacements.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Убираем лишние детали
        text = re.sub(r'\*[^*]+\*', '', text)  # Убираем **жирный** текст
        text = re.sub(r'\[[^\]]+\]', '', text)  # Убираем [ссылки]
        
        # Ограничиваем длину
        if len(text) > 1200:
            text = text[:1197] + "..."
        
        return text.strip()


class SmartHumanizer:
    @staticmethod
    def clean_text(text):
        if not text:
            return ""
        
        # Убираем множественные эмодзи
        text = re.sub(r'(🔥\s*){2,}', '🔥 ', text)
        
        # Убираем упоминания источников
        text = re.sub(r'@\w+|Автор:?\s*\w+|Источник:?[^\n]+', '', text)
        
        # Убираем рекламные вставки
        text = re.sub(r'Подпишись[^\n]+', '', text)
        text = re.sub(r'Подписывайтесь[^\n]+', '', text)
        
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
                
                # Жесткая фильтрация
                if not ContentFilter.is_real_news(content):
                    continue
                
                # Извлекаем только новостную часть
                clean_content = ContentFilter.extract_real_news(content)
                
                if len(clean_content) < 150:
                    continue
                
                if self.db.is_duplicate(clean_content):
                    continue
                
                return file_path, clean_content
            except:
                continue
        
        return None, None
    
    def create_post(self, content):
        if not content:
            return None
        
        # Рерайт
        rewritten = Rewriter.rewrite_news(content)
        
        # Чистка
        clean_content = SmartHumanizer.clean_text(rewritten)
        
        if len(clean_content) > 1200:
            clean_content = clean_content[:1197] + "..."
        
        emoji, title_text, separator = self.get_format()
        news_title = SmartHumanizer.extract_title(content)
        
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
            print("❌ Нет новых качественных новостей")
            return False
        
        print(f"📰 Найдено: {os.path.basename(file_path)}")
        
        post = self.create_post(content)
        
        if not post or len(post) < 100:
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
        print("✅ Только настоящие новости")
        print("✅ Без рекламных рассылок")
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
