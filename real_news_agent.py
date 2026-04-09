import requests
import json
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

class RealNewsAgent:
    """Агент собирает ТОЛЬКО НОВОСТИ (не статьи, не обзоры, не лекции)"""
    
    def __init__(self):
        self.tavily_key = "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"
        
        # ✅ КЛЮЧЕВЫЕ СЛОВА НОВОСТЕЙ (должны быть в заголовке)
        self.news_keywords = [
            'выпустил', 'анонсировал', 'представил', 'запустил', 'открыл',
            'вышла', 'новая версия', 'обновление', 'релиз', 'презентовал',
            'выпущена', 'доступна', 'запущена', 'анонс', 'новинка',
            'релиз', 'обновил', 'добавил', 'интегрировал', 'купил',
            'приобрел', 'инвестировал', 'партнерство', 'сотрудничество',
            'рекорд', 'прорыв', 'впервые', 'установил', 'достиг'
        ]
        
        # ❌ СЛОВА-ИСКЛЮЧЕНИЯ (если есть - это НЕ новость)
        self.exclude_keywords = [
            'введение', 'основы', 'что такое', 'урок', 'лекция', 'курс',
            'туториал', 'руководство', 'обзор технологий', 'тренды',
            'как начать', 'для начинающих', 'обучение', 'шпаргалка',
            'сравнение', 'рейтинг', 'топ', 'лучшие', 'выбор редакции'
        ]
        
        # ✅ ИСТОЧНИКИ НОВОСТЕЙ (а не блоги)
        self.news_domains = [
            'techcrunch.com', 'theverge.com', 'wired.com', 'venturebeat.com',
            'habr.com/ru/news', 'vc.ru', '3dnews.ru', 'cnews.ru',
            'openai.com/news', 'deepmind.com', 'blog.google',
            'microsoft.com/en-us/ai', 'yandex.ru/company/news',
            'sber.ru/news', 'tass.ru/ekonomika/ai'
        ]
    
    def is_real_news(self, title: str, content: str) -> bool:
        """Проверка: является ли это НОВОСТЬЮ"""
        title_lower = title.lower()
        content_lower = content.lower()
        
        # Проверка на слова-исключения
        for excl in self.exclude_keywords:
            if excl in title_lower:
                print(f"   ❌ Исключено (слово '{excl}'): {title[:50]}")
                return False
        
        # Проверка на новостные слова
        has_news_word = any(kw in title_lower for kw in self.news_keywords)
        if not has_news_word:
            print(f"   ❌ Исключено (нет новостных слов): {title[:50]}")
            return False
        
        # Проверка на наличие даты или свежести
        has_date = any(marker in content_lower for marker in [
            'сегодня', 'вчера', 'только что', 'minutes ago', 'hours ago',
            datetime.now().strftime('%Y-%m-%d'),
            datetime.now().strftime('%d.%m.%Y')
        ])
        
        return True
    
    def search_real_news(self):
        """Поиск настоящих новостей"""
        print("🔍 Поиск НАСТОЯЩИХ новостей AI...")
        print("="*60)
        
        # Новостные запросы (а не общие)
        queries = [
            "анонс новой нейросети сегодня",
            "выпустил новую версию AI",
            "релиз искусственного интеллекта",
            "OpenAI Google Microsoft анонс",
            "новости искусственного интеллекта сегодня"
        ]
        
        url = "https://api.tavily.com/search"
        headers = {'Authorization': f'Bearer {self.tavily_key}', 'Content-Type': 'application/json'}
        
        real_news = []
        
        for query in queries:
            payload = {
                "query": f"{query} after:{datetime.now().strftime('%Y-%m-%d')}",
                "search_depth": "advanced",
                "max_results": 10,
                "include_domains": self.news_domains
            }
            
            try:
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    print(f"\n📌 По запросу '{query}': {len(results)} результатов")
                    
                    for r in results:
                        title = r.get('title', '')
                        content = r.get('content', '')
                        
                        if self.is_real_news(title, content):
                            real_news.append(r)
                            print(f"   ✅ НОВОСТЬ: {title[:60]}")
                        else:
                            print(f"   ⏭️ Не новость: {title[:50]}...")
                            
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        return real_news
    
    def parse_full_news(self, url):
        """Парсинг полного текста новости"""
        try:
            response = requests.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            content = soup.find('article') or soup.find(class_=re.compile(r'content|post|news', re.I))
            
            if content:
                paragraphs = content.find_all('p')
                text = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 50])
                if len(text) > 300:
                    return text
            return None
        except:
            return None
    
    def save_news(self, news_list):
        """Сохранение только НОВОСТЕЙ"""
        if not news_list:
            print("\n❌ НАСТОЯЩИХ НОВОСТЕЙ ЗА СЕГОДНЯ НЕ НАЙДЕНО")
            print("💡 Возможно, сегодня не было значимых событий в AI")
            return None
        
        folder = f"real_news_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        os.makedirs(folder, exist_ok=True)
        
        print(f"\n💾 Сохранение {len(news_list)} НАСТОЯЩИХ новостей...")
        
        for i, news in enumerate(news_list, 1):
            full_text = self.parse_full_news(news.get('url', '')) or news.get('content', '')
            
            # Формат для Telegram
            post = f"""
🔥 *НОВОСТЬ* 🔥

*{news.get('title', '')}*

{full_text[:1500]}...

━━━━━━━━━━━━━━━━━━━━━━
📅 {datetime.now().strftime('%d.%m.%Y %H:%M')}
🔗 {news.get('url', '')}

#AIновости #Срочно #Нейросети
"""
            with open(f"{folder}/post_{i}.txt", 'w', encoding='utf-8') as f:
                f.write(post)
            
            print(f"   ✅ {i}. {news.get('title', '')[:60]}")
        
        return folder
    
    def run(self):
        print("="*70)
        print("📰 REAL NEWS AGENT - ТОЛЬКО НАСТОЯЩИЕ НОВОСТИ")
        print("="*70)
        print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        print("="*70)
        
        news = self.search_real_news()
        folder = self.save_news(news)
        
        if folder:
            print(f"\n✅ Результат: {folder}/")
        else:
            print("\n💡 Рекомендация: проверьте вручную https://news.google.com/topics/CAAqJggKIiBDQkFTRWdvSUwyMHZNRGRqTVhZU0FtVnVHZ0pWVXlnQVAB?hl=ru&gl=RU&ceid=RU%3Aru")

if __name__ == "__main__":
    import os
    agent = RealNewsAgent()
    agent.run()
