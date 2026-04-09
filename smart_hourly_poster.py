import requests
import re
import json
import time
import os
import glob
import hashlib
from datetime import datetime
from pathlib import Path

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class SmartHumanizer:
    """Умная хьюманизация текста"""
    
    @staticmethod
    def remove_ai_patterns(text):
        """Удаление AI-паттернов"""
        
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
            r'Обратите внимание:\s*',
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
            'Consequently': 'В итоге',
            'Notably': 'Важно',
            'Significantly': 'Существенно',
            'Particularly': 'Особенно',
            'crucial': 'важный',
            'pivotal': 'ключевой',
            'vibrant': 'активный',
            'landscape': 'среда',
            'showcase': 'показывают',
            'underscore': 'подчеркивают',
            'testament': 'пример',
            'enduring': 'долгий',
            'fostering': 'развивая',
            'enhance': 'улучшать',
        }
        
        for ai_word, human_word in ai_words.items():
            text = re.sub(rf'\b{ai_word}\b', human_word, text, flags=re.IGNORECASE)
        
        # Убираем упоминания авторов
        text = re.sub(r'@\w+|Автор:?\s*\w+|от\s+@\w+', '', text)
        
        # Чистим лишние переносы
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()
    
    @staticmethod
    def is_quality_news(text):
        """Проверка: новость или личная история"""
        
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
            r'компания\s+\w+\s+(выпустила|представила|анонсировала)',
            r'openai|google|microsoft|meta|amazon|apple|sber|yandex'
        ]
        
        text_lower = text.lower()
        for pattern in good_patterns:
            if re.search(pattern, text_lower):
                return True
        
        # Если есть упоминание крупной компании - пропускаем через фильтр
        companies = ['openai', 'google', 'microsoft', 'meta', 'amazon', 'apple', 'sber', 'yandex']
        if any(company in text_lower for company in companies):
            # Дополнительная проверка на отсутствие личных историй
            if not re.search(r'\b(я|меня|мне|мой)\b', text_lower):
                return True
        
        return False


class UniquePoster:
    """Уникальный постинг без дублей"""
    
    def __init__(self):
        self.db_file = "posted_news_db.json"
        self.load_db()
    
    def load_db(self):
        """Загрузка базы опубликованных новостей"""
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {
                'posted_hashes': [],      # Хеши контента
                'posted_titles': [],      # Заголовки
                'posted_urls': [],        # Ссылки
                'history': []             # Полная история
            }
    
    def save_db(self):
        """Сохранение базы"""
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, ensure_ascii=False, indent=2)
    
    def get_content_hash(self, text):
        """Получение хеша контента для проверки дублей"""
        # Берем первые 200 символов и нормализуем
        normalized = re.sub(r'\s+', ' ', text[:300].lower())
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def extract_title(self, text):
        """Извлечение заголовка из текста"""
        lines = text.split('\n')
        for line in lines[:10]:
            line = line.strip()
            if len(line) > 15 and len(line) < 150:
                # Убираем эмодзи в начале
                clean_line = re.sub(r'^[🔥⚡️💥✨🎯📢]+', '', line).strip()
                if clean_line and not clean_line.startswith('http'):
                    return clean_line[:100]
        return None
    
    def extract_url(self, text):
        """Извлечение URL из текста"""
        urls = re.findall(r'https?://[^\s]+', text)
        return urls[0] if urls else None
    
    def is_duplicate(self, text):
        """Проверка на дубликат"""
        content_hash = self.get_content_hash(text)
        
        if content_hash in self.db['posted_hashes']:
            return True, "hash"
        
        title = self.extract_title(text)
        if title and title in self.db['posted_titles']:
            return True, "title"
        
        url = self.extract_url(text)
        if url and url in self.db['posted_urls']:
            return True, "url"
        
        return False, None
    
    def mark_as_posted(self, text, file_path=None):
        """Отметить новость как опубликованную"""
        content_hash = self.get_content_hash(text)
        title = self.extract_title(text)
        url = self.extract_url(text)
        
        self.db['posted_hashes'].append(content_hash)
        if title:
            self.db['posted_titles'].append(title)
        if url:
            self.db['posted_urls'].append(url)
        
        self.db['history'].append({
            'timestamp': datetime.now().isoformat(),
            'title': title,
            'hash': content_hash,
            'file': file_path,
            'url': url
        })
        
        # Ограничиваем размер истории (последние 1000)
        if len(self.db['posted_hashes']) > 1000:
            self.db['posted_hashes'] = self.db['posted_hashes'][-1000:]
        if len(self.db['posted_titles']) > 1000:
            self.db['posted_titles'] = self.db['posted_titles'][-1000:]
        
        self.save_db()


class UniqueFormatPoster:
    """Уникальный формат постов для Telegram"""
    
    # Разные варианты оформления (чередуются)
    FORMATS = [
        {
            'header': '🤖 **СВЕЖАЯ НОВОСТЬ** 🤖',
            'separator': '▫️▫️▫️▫️▫️▫️▫️▫️▫️▫️',
            'footer_emoji': '📌'
        },
        {
            'header': '📢 **НОВОСТЬ ЧАСА** 📢',
            'separator': '▪️▪️▪️▪️▪️▪️▪️▪️▪️▪️',
            'footer_emoji': '🔗'
        },
        {
            'header': '⚡️ **В ЭТОТ ЧАС** ⚡️',
            'separator': '─━─━─━─━─━─━─',
            'footer_emoji': '🎯'
        },
        {
            'header': '🔥 **ТОЛЬКО ЧТО** 🔥',
            'separator': '• • • • • • • • • •',
            'footer_emoji': '💡'
        },
        {
            'header': '📰 **НОВОСТЬ** 📰',
            'separator': '━━━━━━━━━━━━━━━━━━',
            'footer_emoji': '🔍'
        }
    ]
    
    def __init__(self):
        self.format_index = 0
    
    def get_next_format(self):
        """Циклическое получение следующего формата"""
        fmt = self.FORMATS[self.format_index]
        self.format_index = (self.format_index + 1) % len(self.FORMATS)
        return fmt
    
    def create_unique_post(self, content, news_title=None):
        """Создание уникального поста с чередующимся оформлением"""
        
        # Хьюманизируем контент
        humanized = SmartHumanizer.remove_ai_patterns(content)
        
        # Ограничиваем длину
        if len(humanized) > 1800:
            humanized = humanized[:1797] + "..."
        
        # Получаем формат для этого поста
        fmt = self.get_next_format()
        
        # Извлекаем или создаем заголовок
        if not news_title:
            news_title = SmartHumanizer.extract_title(content)
        
        if not news_title or len(news_title) < 10:
            news_title = "Новости искусственного интеллекта"
        
        # Очищаем заголовок от лишнего
        news_title = re.sub(r'^[🔥⚡️💥✨🎯📢]+', '', news_title).strip()
        
        # Собираем пост в уникальном формате
        post = f"""{fmt['header']}

**{news_title}**

{humanized}

{fmt['separator']}

{fmt['footer_emoji']} @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
🏷 #AIновости #Нейросети #{datetime.now().strftime('%d%m%Y')}"""
        
        return post


class HourlySmartPoster:
    """Умный постинг 1 новости в час без дублей"""
    
    def __init__(self):
        self.poster = UniqueFormatPoster()
        self.db = UniquePoster()
    
    def find_best_news(self):
        """Найти лучшую непросмотренную новость"""
        
        news_files = []
        patterns = [
            "real_news_*/post_*.txt",
            "news_summary_*/telegram/*.txt",
            "full_news_*/telegram/*.txt",
            "*.txt"
        ]
        
        for pattern in patterns:
            found = glob.glob(pattern)
            # Исключаем системные файлы
            found = [f for f in found if not os.path.basename(f).startswith('posted_')]
            news_files.extend(found)
        
        # Сортируем по времени создания
        news_files.sort(key=os.path.getctime, reverse=True)
        
        best_file = None
        best_score = -1
        
        for file_path in news_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Проверка на качество новости
                if not SmartHumanizer.is_quality_news(content):
                    continue
                
                # Проверка на дубликат
                is_dup, dup_type = self.db.is_duplicate(content)
                if is_dup:
                    print(f"   ⏭️ Дубликат ({dup_type}): {os.path.basename(file_path)}")
                    continue
                
                # Оценка качества
                score = 0
                score += min(len(content) / 500, 5)  # Длина
                
                if any(company in content.lower() for company in ['openai', 'google', 'microsoft']):
                    score += 3
                
                if '—' not in content:
                    score += 1
                
                if score > best_score:
                    best_score = score
                    best_file = file_path
                    
            except Exception as e:
                continue
        
        return best_file, best_score
    
    def post_one_news(self):
        """Публикация одной уникальной новости"""
        
        print(f"\n🔍 Поиск новой уникальной новости...")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        best_file, score = self.find_best_news()
        
        if not best_file:
            print("❌ Нет новых качественных новостей")
            return False
        
        print(f"📰 Найдено: {os.path.basename(best_file)} (оценка: {score})")
        
        try:
            with open(best_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Извлекаем заголовок
            title = UniquePoster.extract_title(content)
            
            # Создаем уникальный пост
            post = self.poster.create_unique_post(content, title)
            
            # Отправляем
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {
                'chat_id': CHANNEL_ID,
                'text': post,
                'parse_mode': 'Markdown',
                'disable_web_page_preview': True
            }
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                # Отмечаем как опубликованное
                self.db.mark_as_posted(content, best_file)
                print(f"✅ Опубликовано в {datetime.now().strftime('%H:%M')}")
                return True
            else:
                print(f"❌ Ошибка отправки: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def run_hourly(self):
        """Запуск цикла 1 новость в час"""
        
        print("="*60)
        print("⏰ УМНЫЙ ПОСТИНГ: 1 НОВОСТЬ В ЧАС")
        print("="*60)
        print(f"📢 Канал: {CHANNEL_ID}")
        print(f"🕐 Старт: {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        print("✅ Без дублей")
        print("✅ Уникальное оформление")
        print("✅ Только качественные новости")
        print("="*60)
        
        while True:
            success = self.post_one_news()
            
            if not success:
                print("⏳ Нет новых новостей, ждем 30 минут...")
                time.sleep(1800)
                continue
            
            # Ждем 1 час до следующей публикации
            print(f"\n⏳ Следующая публикация через 1 час")
            next_hour = (datetime.now().timestamp() + 3600)
            print(f"   {datetime.now().strftime('%H:%M:%S')} → {datetime.fromtimestamp(next_hour).strftime('%H:%M:%S')}")
            
            for _ in range(360):  # 360 * 10 сек = 1 час
                time.sleep(10)
    
    def run_once(self):
        """Разовый запуск для теста"""
        self.post_one_news()
    
    def show_stats(self):
        """Показать статистику"""
        print("\n📊 СТАТИСТИКА ПУБЛИКАЦИЙ")
        print("="*40)
        print(f"Опубликовано новостей: {len(self.db.db['posted_hashes'])}")
        print(f"Уникальных заголовков: {len(self.db.db['posted_titles'])}")
        print(f"База данных: {self.db.db_file}")
        
        if self.db.db['history']:
            last = self.db.db['history'][-1]
            print(f"\nПоследняя публикация:")
            print(f"  • Время: {last['timestamp']}")
            print(f"  • Заголовок: {last['title'][:50]}...")


def main():
    import sys
    
    poster = HourlySmartPoster()
    
    if len(sys.argv) > 1:
        if sys.argv[1] == '--hourly':
            poster.run_hourly()
        elif sys.argv[1] == '--once':
            poster.run_once()
        elif sys.argv[1] == '--stats':
            poster.show_stats()
        else:
            print("Использование:")
            print("  --hourly  : Запуск 1 новость в час")
            print("  --once    : Разовая публикация")
            print("  --stats   : Показать статистику")
    else:
        poster.run_once()

if __name__ == "__main__":
    main()
