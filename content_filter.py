import re

class ContentCleaner:
    """Очистка контента от упоминаний других авторов и каналов"""
    
    @staticmethod
    def remove_author_mentions(text):
        """Удаление всех упоминаний авторов"""
        
        # Паттерны для удаления
        patterns = [
            r'Автор:?\s*[А-Яа-я\s]+',
            r'Источник:?\s*@?\w+',
            r'Пост от @\w+',
            r'делится @\w+',
            r'рассказывает @\w+',
            r'пишет @\w+',
            r'от автора @\w+',
            r'слова @\w+',
            r'канал @\w+',
            r'telegram-канал @\w+',
            r'наш канал @\w+',
            r'подписывайтесь на @\w+',
            r'переходите на @\w+',
            r'больше новостей в @\w+',
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Удаляем голые упоминания
        text = re.sub(r'@\w+', '', text)
        
        return text.strip()
    
    @staticmethod
    def make_it_mine(text):
        """Делаем контент авторским"""
        
        # Заменяем фразы
        replacements = {
            'ученые создали': 'создана',
            'исследователи обнаружили': 'обнаружено',
            'компания представила': 'представлена',
            'разработчики выпустили': 'выпущена',
            'по данным источника': 'по информации',
            'как сообщает': '',
            'со ссылкой на': '',
            'передает': '',
        }
        
        for old, new in replacements.items():
            text = re.sub(old, new, text, flags=re.IGNORECASE)
        
        return text

# Тест
if __name__ == "__main__":
    test_text = """
    Автор: @ivan_petrov
    Пост от @ai_news_channel
    Ученые создали новую нейросеть. Компания OpenAI представила GPT-5.
    Подписывайтесь на @my_channel для новостей!
    """
    
    cleaned = ContentCleaner.remove_author_mentions(test_text)
    final = ContentCleaner.make_it_mine(cleaned)
    
    print("Оригинал:", test_text)
    print("Очищено:", cleaned)
    print("Финальный:", final)
