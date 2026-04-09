import requests
import re
import json
import time
import os
import glob
from datetime import datetime
from pathlib import Path

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class Humanizer:
    """Класс для удаления AI-признаков из текста"""
    
    # ❌ AI-слова для замены
    AI_WORDS = {
        'additionally': 'кроме того',
        'align with': 'соответствует',
        'crucial': 'важный',
        'delve': 'разбираться',
        'emphasizing': 'подчеркивая',
        'enduring': 'долговременный',
        'enhance': 'улучшать',
        'fostering': 'развивая',
        'garner': 'получать',
        'highlight': 'показывать',
        'interplay': 'взаимодействие',
        'intricate': 'сложный',
        'pivotal': 'ключевой',
        'showcase': 'демонстрировать',
        'testament': 'свидетельство',
        'underscore': 'подчеркивать',
        'vibrant': 'активный',
        'landscape': 'среда',
        'tapestry': 'совокупность',
    }
    
    # ❌ Паттерны для удаления
    PATTERNS_TO_REMOVE = [
        (r'В заключени[еи][^.]*\.', ''),
        (r'Подводя итог[^.]*\.', ''),
        (r'Как уже отмечалось[^.]*\.', ''),
        (r'Стоит отметить, что\s*', ''),
        (r'Важно подчеркнуть, что\s*', ''),
        (r'Очевидно, что\s*', ''),
        (r'Безусловно,\s*', ''),
        (r'В современном мире\s*', ''),
        (r'В сегодняшних реалиях\s*', ''),
        (r'Нельзя не отметить,\s*', ''),
        (r'Следует заметить,\s*', ''),
        (r'Обратите внимание:\s*', ''),
        (r'Во-первых,\s*', ''),
        (r'Во-вторых,\s*', ''),
        (r'В-третьих,\s*', ''),
    ]
    
    @classmethod
    def remove_ai_patterns(cls, text):
        """Удаление основных AI-паттернов"""
        
        # Убираем двойные эмодзи
        text = re.sub(r'(🔥\s*){2,}', '🔥 ', text)
        text = re.sub(r'(⚡️\s*){2,}', '⚡️ ', text)
        
        # Убираем дублирование слов
        text = re.sub(r'(НОВОСТЬ\s*){2,}', 'НОВОСТЬ\n\n', text, flags=re.IGNORECASE)
        
        # Убираем шаблонные фразы
        for pattern, replacement in cls.PATTERNS_TO_REMOVE:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        # Заменяем AI-слова
        for ai_word, human_word in cls.AI_WORDS.items():
            text = re.sub(rf'\b{ai_word}\b', human_word, text, flags=re.IGNORECASE)
        
        # Убираем эмодзи из середины текста
        text = re.sub(r'[🚀💡🎯✨💎🌟⭐️]', '', text)
        
        # Убираем множественные переносы
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Убираем упоминания авторов
        text = re.sub(r'@\w+|Автор:?\s*\w+', '', text)
        
        return text.strip()
    
    @classmethod
    def humanize(cls, text):
        """Основной метод хьюманизации"""
        
        # 1. Удаляем AI-паттерны
        text = cls.remove_ai_patterns(text)
        
        # 2. Добавляем живые фразы (иногда)
        if len(text) > 300:
            live_phrases = [
                "\n\n👉 Кстати, вот что еще интересно:",
                "\n\n📌 Суть в том, что",
                "\n\n🎯 Главное тут —",
            ]
            # Добавляем не всегда, чтобы не было шаблона
            if hash(text) % 5 == 0:
                text += live_phrases[hash(text) % len(live_phrases)]
        
        return text
    
    @classmethod
    def is_real_news(cls, text):
        """Проверка: настоящая новость или нет"""
        
        # ❌ Плохие паттерны (личные истории)
        bad_patterns = [
            r'я\s+выпустил', r'мой\s+опыт', r'моя\s+история',
            r'скачивания', r'конверсия', r'баги', r'исправил',
            r'я\s+сделал', r'мне\s+написали', r'письма\s+с\s+описанием'
        ]
        
        for pattern in bad_patterns:
            if re.search(pattern, text.lower()):
                return False
        
        # ✅ Хорошие паттерны
        good_patterns = [
            r'выпустил\s+новую\s+версию', r'анонсировал', r'представил',
            r'запустил', r'открыл', r'вышла', r'релиз', r'презентовал'
        ]
        
        for pattern in good_patterns:
            if re.search(pattern, text.lower()):
                return True
        
        return False


class HourlyPoster:
    """Постинг 1 лучшей новости в час"""
    
    def __init__(self):
        self.last_posted_file = "hourly_posted.json"
        self.load_history()
    
    def load_history(self):
        if os.path.exists(self.last_posted_file):
            with open(self.last_posted_file, 'r') as f:
                self.history = json.load(f)
        else:
            self.history = {}
    
    def save_history(self):
        with open(self.last_posted_file, 'w') as f:
            json.dump(self.history, f, indent=2)
    
    def find_best_news(self):
        """Найти лучшую непросмотренную новость"""
        
        # Ищем файлы с новостями
        news_files = []
        patterns = [
            "real_news_*/post_*.txt",
            "news_summary_*/telegram/*.txt",
            "*.txt"
        ]
        
        for pattern in patterns:
            found = glob.glob(pattern)
            news_files.extend(found)
        
        # Фильтруем уже опубликованные
        new_files = [f for f in news_files if f not in self.history]
        
        if not new_files:
            return None
        
        # Оцениваем каждую новость
        best_file = None
        best_score = -1
        
        for file_path in new_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Проверяем что это новость
                if not Humanizer.is_real_news(content):
                    continue
                
                # Оценка качества
                score = 0
                score += min(len(content) / 500, 5)  # Длина
                
                if '🔥' in content:
                    score += 1
                if '—' not in content:  # Без длинных тире
                    score += 1
                if 'кроме того' not in content.lower():
                    score += 1
                
                if score > best_score:
                    best_score = score
                    best_file = file_path
                    
            except Exception as e:
                continue
        
        return best_file
    
    def create_post(self, content):
        """Создание поста из новости"""
        
        # Хьюманизируем
        humanized = Humanizer.humanize(content)
        
        # Ограничиваем длину
        if len(humanized) > 2000:
            humanized = humanized[:1997] + "..."
        
        # Форматируем
        post = f"""🔥 **НОВОСТЬ**

{humanized}

---
📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}
📌 @DenisBukhancov_CRM_AI

#AI #Нейросети #СвежаяНовость"""
        
        return post
    
    def send_message(self, text):
        """Отправка в Telegram"""
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
            print(f"❌ Ошибка: {e}")
            return False
    
    def post_one_news(self):
        """Публикация одной новости"""
        
        print(f"\n🔍 Поиск лучшей новости...")
        
        best_file = self.find_best_news()
        
        if not best_file:
            print("❌ Нет новых новостей для публикации")
            return False
        
        print(f"📰 Найдено: {os.path.basename(best_file)}")
        
        try:
            with open(best_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            post = self.create_post(content)
            
            print(f"📤 Публикация...")
            
            if self.send_message(post):
                self.history[best_file] = datetime.now().isoformat()
                self.save_history()
                print(f"✅ Опубликовано в {datetime.now().strftime('%H:%M')}")
                return True
            else:
                print(f"❌ Ошибка отправки")
                return False
                
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            return False
    
    def run_once(self):
        """Разовый запуск"""
        self.post_one_news()
    
    def run_hourly(self):
        """Запуск с ожиданием часа между постами"""
        print("="*60)
        print("⏰ ПОСТИНГ 1 НОВОСТИ В ЧАС")
        print("="*60)
        print(f"📢 Канал: {CHANNEL_ID}")
        print(f"🕐 Старт: {datetime.now().strftime('%H:%M:%S')}")
        print("="*60)
        
        while True:
            # Публикуем новость
            success = self.post_one_news()
            
            if not success:
                print("⏳ Нет новостей, ждем 30 минут...")
                time.sleep(1800)  # 30 минут
                continue
            
            # Ждем 1 час до следующей публикации
            print(f"\n⏳ Следующая публикация через 1 час...")
            print(f"   {datetime.now().strftime('%H:%M:%S')} → {(datetime.now().timestamp() + 3600)}")
            
            # Пауза с возможностью остановки
            for _ in range(360):  # 360 * 10 сек = 1 час
                time.sleep(10)


def main():
    import sys
    
    poster = HourlyPoster()
    
    if len(sys.argv) > 1 and sys.argv[1] == '--hourly':
        # Запуск в режиме "1 новость в час"
        poster.run_hourly()
    elif len(sys.argv) > 1 and sys.argv[1] == '--once':
        # Разовая публикация
        poster.run_once()
    else:
        # По умолчанию - разовая
        poster.run_once()

if __name__ == "__main__":
    main()
