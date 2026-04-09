import requests
import re
import json
import time
import os
import hashlib
import random
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from typing import Dict, List, Tuple, Optional

# ============================================================
# КОНФИГУРАЦИЯ
# ============================================================
BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
TAVILY_KEY = "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"

NEWS_SOURCES = [
    "habr.com/ru/news/", "vc.ru", "3dnews.ru", "cnews.ru", "it-world.ru",
    "techcrunch.com", "theverge.com", "wired.com", "venturebeat.com",
    "arstechnica.com", "zdnet.com"
]

# ============================================================
# ПЕРЕВОДЧИК
# ============================================================
class SimpleTranslator:
    def __init__(self):
        self.cache = {}
    
    def translate_to_russian(self, text: str) -> str:
        if not text:
            return ""
        if re.search(r'[а-яА-Я]', text):
            return text
        
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]
        
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {'q': text[:500], 'langpair': 'en|ru', 'de': 'denisbuhancov@gmail.com'}
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                translated = data.get('responseData', {}).get('translatedText', text)
                translated = re.sub(r'\[[^\]]+\]', '', translated)
                self.cache[text_hash] = translated
                return translated
        except:
            pass
        return text

# ============================================================
# ПОИСК НОВОСТЕЙ
# ============================================================
class NewsHunter:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({'User-Agent': 'Mozilla/5.0'})
        self.translator = SimpleTranslator()
    
    def search_news(self, hours_back: int = 6) -> List[Dict]:
        print(f"\n🔍 Поиск новостей за последние {hours_back} часов...")
        
        since_time = (datetime.now() - timedelta(hours=hours_back)).strftime('%Y-%m-%d')
        
        queries = [
            f"artificial intelligence news after:{since_time}",
            f"AI breakthrough new model after:{since_time}",
            f"нейросети новая модель after:{since_time}",
            f"LLM release open source after:{since_time}"
        ]
        
        url = "https://api.tavily.com/search"
        headers = {'Authorization': f'Bearer {TAVILY_KEY}', 'Content-Type': 'application/json'}
        
        all_news = []
        
        for query in queries:
            try:
                payload = {
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": 10,
                    "include_domains": NEWS_SOURCES
                }
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    for r in results:
                        # Проверяем, что контент не обрезан
                        content = r.get('content', '')
                        if content.endswith('...') or content.endswith('…'):
                            # Если контент обрезан, пытаемся получить полный
                            full_content = self.parse_full_article(r.get('url', ''))
                            content = full_content if full_content else content
                        
                        all_news.append({
                            'title': self.translator.translate_to_russian(r.get('title', '')),
                            'url': r.get('url', ''),
                            'content': self.translator.translate_to_russian(content),
                            'score': r.get('score', 0),
                            'source': self._extract_source(r.get('url', '')),
                        })
                    print(f"   ✅ {query[:40]}... -> {len(results)} рез.")
                time.sleep(1)
            except Exception as e:
                print(f"   ❌ Ошибка: {e}")
        
        # Удаляем дубликаты
        unique_news = []
        seen_urls = set()
        for news in all_news:
            if news['url'] not in seen_urls:
                seen_urls.add(news['url'])
                unique_news.append(news)
        
        print(f"\n📊 Всего найдено: {len(unique_news)} новостей")
        return unique_news
    
    def parse_full_article(self, url: str) -> Optional[str]:
        """Парсинг полной статьи - гарантированно полный текст"""
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Удаляем мусор
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
            
            # Ищем основной контент
            content = soup.find('article') or soup.find(class_=re.compile(r'content|post|entry|body', re.I))
            
            if content:
                paragraphs = content.find_all('p')
                # Берем все параграфы, не обрезаем
                text_parts = []
                for p in paragraphs:
                    p_text = p.get_text(strip=True)
                    if len(p_text) > 30:  # Пропускаем слишком короткие
                        text_parts.append(p_text)
                
                full_text = '\n\n'.join(text_parts)
                
                # Проверяем, что текст не обрезан
                if len(full_text) > 500 and not full_text.endswith('...'):
                    return self.translator.translate_to_russian(full_text)
                
                # Если все еще обрезан, пробуем другой метод
                text = content.get_text(separator='\n', strip=True)
                if len(text) > 500 and not text.endswith('...'):
                    return self.translator.translate_to_russian(text)
            
            return None
        except Exception as e:
            print(f"   ⚠️ Парсинг не удался: {e}")
            return None
    
    def _extract_source(self, url: str) -> str:
        for source in NEWS_SOURCES:
            if source in url:
                return source.split('.')[0].capitalize()
        return "Unknown"

# ============================================================
# ПРОВЕРКА ЦЕЛОСТНОСТИ ТЕКСТА
# ============================================================
class TextValidator:
    """Проверка что текст полный, а не обрезанный"""
    
    @staticmethod
    def is_complete(text: str) -> bool:
        """Проверка: текст не обрезан и имеет смысл"""
        if not text:
            return False
        
        # Проверка на обрезание
        if text.strip().endswith('...') or text.strip().endswith('…'):
            return False
        
        # Проверка на минимальную длину
        if len(text) < 300:
            return False
        
        # Должно быть хотя бы 3 предложения
        sentences = re.split(r'[.!?]+', text)
        if len(sentences) < 3:
            return False
        
        return True
    
    @staticmethod
    def fix_truncated_text(text: str, full_text: str) -> str:
        """Замена обрезанного текста на полный"""
        if not full_text:
            return text
        
        # Если полный текст значительно длиннее и не обрезан
        if len(full_text) > len(text) * 1.5 and not full_text.endswith('...'):
            return full_text
        
        return text

# ============================================================
# БАЗА ДАННЫХ
# ============================================================
class NewsDatabase:
    def __init__(self):
        self.db_file = "published_news_db.json"
        self.load()
    
    def load(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'urls': [], 'hashes': []}
    
    def save(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def is_published(self, url: str) -> bool:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return url in self.db['urls'] or url_hash in self.db['hashes']
    
    def mark_published(self, url: str):
        self.db['urls'].append(url)
        self.db['hashes'].append(hashlib.md5(url.encode()).hexdigest())
        self.save()

# ============================================================
# HUMANIZER
# ============================================================
class HydraHumanizer:
    @staticmethod
    def humanize(text: str) -> str:
        if not text:
            return ""
        
        # Убираем шаблонные фразы
        patterns = [
            (r'В современном быстро меняющемся мире\s*', ''),
            (r'Стоит отметить, что\s*', ''),
            (r'Важно подчеркнуть,\s*', ''),
            (r'Очевидно, что\s*', ''),
            (r'Безусловно,\s*', ''),
        ]
        for pattern, repl in patterns:
            text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
        
        # Убираем множественные переносы
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text.strip()

# ============================================================
# AI-КАРДИОГРАММА
# ============================================================
class AICardiogram:
    @staticmethod
    def extract_tech_stack(content: str) -> Dict:
        tech = {'architecture': '—', 'parameters': '—', 'context': '—'}
        content_lower = content.lower()
        
        if 'transformer' in content_lower:
            tech['architecture'] = 'Transformer'
        elif 'moe' in content_lower or 'mixture of experts' in content_lower:
            tech['architecture'] = 'MoE'
        elif 'diffusion' in content_lower:
            tech['architecture'] = 'Diffusion'
        
        param_match = re.search(r'(\d+(?:\.\d+)?)\s*[Bb]', content)
        if param_match:
            tech['parameters'] = f"{param_match.group(1)}B"
        
        ctx_match = re.search(r'(\d+(?:\.\d+)?)\s*([KkMm]?)\s*токен', content_lower)
        if ctx_match:
            tech['context'] = f"{ctx_match.group(1)}{ctx_match.group(2).upper()} токенов"
        
        return tech
    
    @classmethod
    def format(cls, title: str, content: str, source: str) -> str:
        # Проверяем целостность текста
        if not TextValidator.is_complete(content):
            return None  # Не публикуем обрезанные новости
        
        humanized = HydraHumanizer.humanize(content)
        
        # Берем первые 3-4 предложения для сути
        sentences = re.split(r'[.!?]+', humanized)
        essence_parts = []
        for s in sentences[:4]:
            s = s.strip()
            if len(s) > 30:
                essence_parts.append(s)
        
        essence = '. '.join(essence_parts)
        if len(essence) > 500:
            essence = essence[:497] + "..."
        
        tech = cls.extract_tech_stack(content)
        
        post = f"""⚡️ **{title[:80]}**

📅 Статус: 🟢 НОВОСТЬ
🏷 Теги: #AI #LLM #TechNews

---

🧠 **Суть**

{essence}

---

⚙️ **Под капотом**

`Архитектура:` {tech['architecture']}
`Параметры:` {tech['parameters']}
`Контекст:` {tech['context']}

---

🔮 **Почему это важно**

Технология меняет подход к управлению данными в ИИ. Если решение масштабируется, крупные игроки будут вынуждены пересмотреть свои стратегии.

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AINews #TechAnalysis"""
        
        return post

# ============================================================
# ГЛАВНЫЙ АГЕНТ
# ============================================================
class FinalNewsAgent:
    def __init__(self):
        self.hunter = NewsHunter()
        self.db = NewsDatabase()
    
    def send_to_telegram(self, text: str) -> bool:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        try:
            r = requests.post(url, json={'chat_id': CHANNEL_ID, 'text': text}, timeout=30)
            return r.status_code == 200
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False
    
    def run_cycle(self):
        print("="*70)
        print("🚀 FINAL NEWS AGENT - ПОЛНЫЕ НОВОСТИ")
        print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("🌍 С переводом на русский | Без обрезанных текстов")
        print("="*70)
        
        news_list = self.hunter.search_news(hours_back=6)
        
        if not news_list:
            print("\n❌ Новостей не найдено")
            return
        
        # Фильтрация уже опубликованных
        new_news = []
        for news in news_list:
            if not self.db.is_published(news['url']):
                new_news.append(news)
        
        if not new_news:
            print("\n❌ Нет новых новостей")
            return
        
        print(f"\n📊 Новых новостей: {len(new_news)}")
        
        # Проверяем каждую новость на целостность
        valid_news = []
        for news in new_news:
            if TextValidator.is_complete(news['content']):
                valid_news.append(news)
                print(f"   ✅ Полная: {news['title'][:50]}...")
            else:
                print(f"   ⏭️ Обрезана: {news['title'][:50]}...")
        
        if not valid_news:
            print("\n❌ Нет полных новостей (все обрезаны)")
            return
        
        # Берем первую полную новость
        best_news = valid_news[0]
        
        print(f"\n🏆 Публикуем:")
        print(f"📰 {best_news['title'][:80]}")
        print(f"🔗 {best_news['url']}")
        
        # Создаем пост
        post = AICardiogram.format(
            title=best_news['title'],
            content=best_news['content'],
            source=best_news.get('source', 'Unknown')
        )
        
        if not post:
            print("\n❌ Не удалось создать пост (обрезанный текст)")
            return
        
        if self.send_to_telegram(post):
            self.db.mark_published(best_news['url'])
            print(f"\n✅ ОПУБЛИКОВАНО!")
            print(f"📏 Длина текста: {len(best_news['content'])} символов")
        else:
            print(f"\n❌ Ошибка публикации")
        
        print("\n" + "="*70)
        print("⏳ Следующий запуск через 6 часов")
        print("="*70)
    
    def run_once(self):
        self.run_cycle()


if __name__ == "__main__":
    agent = FinalNewsAgent()
    agent.run_once()
