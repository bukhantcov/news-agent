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
BOT_TOKEN = os.environ.get("BOT_TOKEN", "")
CHANNEL_ID = "@DenisBukhancov_CRM_AI"
TAVILY_KEY = "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"

# Источники новостей
NEWS_SOURCES = [
    "habr.com/ru/news/", "vc.ru", "3dnews.ru", "cnews.ru", "it-world.ru",
    "techcrunch.com", "theverge.com", "wired.com", "venturebeat.com",
    "arstechnica.com", "zdnet.com"
]

# ============================================================
# 0. ПРОСТОЙ ПЕРЕВОДЧИК (без googletrans)
# ============================================================
class SimpleTranslator:
    """Простой переводчик с использованием внешнего API"""
    
    def __init__(self):
        self.cache = {}
    
    def translate_to_russian(self, text: str) -> str:
        """Перевод текста на русский язык через бесплатный API"""
        if not text:
            return ""
        
        # Проверяем, есть ли русские буквы
        if re.search(r'[а-яА-Я]', text):
            return text
        
        # Проверяем кэш
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self.cache:
            return self.cache[text_hash]
        
        # Пробуем перевести через MyMemory API (бесплатно)
        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                'q': text[:500],  # Ограничиваем длину
                'langpair': 'en|ru',
                'de': 'denisbuhancov@gmail.com'
            }
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                translated = data.get('responseData', {}).get('translatedText', text)
                # Убираем мусорные символы
                translated = re.sub(r'\[[^\]]+\]', '', translated)
                self.cache[text_hash] = translated
                return translated
        except Exception as e:
            print(f"   ⚠️ Ошибка перевода: {e}")
        
        # Если перевод не удался, возвращаем оригинал
        return text
    
    def translate_news(self, news: Dict) -> Dict:
        """Перевод всей новости"""
        if news.get('title'):
            news['title_original'] = news['title']
            news['title'] = self.translate_to_russian(news['title'])
        
        if news.get('content'):
            news['content_original'] = news['content']
            news['content'] = self.translate_to_russian(news['content'])
        
        return news

# ============================================================
# 1. ПОИСК НОВОСТЕЙ
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
            f"OpenAI Google Microsoft news after:{since_time}"
        ]
        
        url = "https://api.tavily.com/search"
        headers = {'Authorization': f'Bearer {TAVILY_KEY}', 'Content-Type': 'application/json'}
        
        all_news = []
        
        for query in queries:
            try:
                payload = {
                    "query": query,
                    "search_depth": "advanced",
                    "max_results": 8,
                    "include_domains": NEWS_SOURCES
                }
                response = requests.post(url, json=payload, headers=headers, timeout=30)
                
                if response.status_code == 200:
                    results = response.json().get('results', [])
                    for r in results:
                        # Переводим на русский
                        title_ru = self.translator.translate_to_russian(r.get('title', ''))
                        content_ru = self.translator.translate_to_russian(r.get('content', ''))
                        
                        all_news.append({
                            'title': title_ru,
                            'title_original': r.get('title', ''),
                            'url': r.get('url', ''),
                            'content': content_ru,
                            'content_original': r.get('content', ''),
                            'score': r.get('score', 0),
                            'source': self._extract_source(r.get('url', '')),
                            'found_at': datetime.now().isoformat()
                        })
                    print(f"   ✅ {query[:40]}... -> {len(results)} рез. (переведено)")
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
        
        print(f"\n📊 Всего найдено: {len(unique_news)} уникальных новостей")
        return unique_news
    
    def parse_full_article(self, url: str) -> Optional[str]:
        try:
            response = self.session.get(url, timeout=15)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
                tag.decompose()
            
            content = soup.find('article') or soup.find(class_=re.compile(r'content|post|entry', re.I))
            
            if content:
                paragraphs = content.find_all('p')
                text = ' '.join([p.get_text(strip=True) for p in paragraphs if len(p.get_text()) > 40])
                if len(text) > 300:
                    return self.translator.translate_to_russian(text)
            return None
        except:
            return None
    
    def _extract_source(self, url: str) -> str:
        for source in NEWS_SOURCES:
            if source in url:
                return source.split('.')[0].capitalize()
        return "Unknown"

# ============================================================
# 2. АНАЛИЗ ВИРАЛЬНОСТИ
# ============================================================
class ViralityAnalyzer:
    @staticmethod
    def analyze(news: Dict) -> Dict:
        content = news.get('content', '') + news.get('title', '')
        base_score = news.get('score', 0.5) * 100
        length_bonus = min(len(content) / 1000, 20)
        
        virality_score = min(base_score + length_bonus, 100)
        
        return {
            'score': virality_score,
            'level': '🔥' * min(int(virality_score / 20), 5) if virality_score > 40 else '📰'
        }

# ============================================================
# 3. БАЗА ДАННЫХ
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
    
    def is_published(self, url: str, title: str) -> bool:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        title_hash = hashlib.md5(title.lower().encode()).hexdigest()
        return url in self.db['urls'] or url_hash in self.db['hashes'] or title_hash in self.db['hashes']
    
    def mark_published(self, url: str, title: str):
        self.db['urls'].append(url)
        self.db['hashes'].append(hashlib.md5(url.encode()).hexdigest())
        self.db['hashes'].append(hashlib.md5(title.lower().encode()).hexdigest())
        self.save()

# ============================================================
# 4. HUMANIZER
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
        
        text = re.sub(r'!{2,}', '!', text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

# ============================================================
# 5. AI-КАРДИОГРАММА
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
    def format(cls, title: str, content: str, virality: Dict) -> str:
        humanized = HydraHumanizer.humanize(content)
        if len(humanized) > 500:
            humanized = humanized[:497] + "..."
        
        tech = cls.extract_tech_stack(content)
        
        post = f"""⚡️ **{title[:80]}**

📅 Статус: 🟢 РЕЛИЗ

---

🧠 **Суть**

{humanized}

---

⚙️ **Под капотом**

`Архитектура:` {tech['architecture']}
`Параметры:` {tech['parameters']}
`Контекст:` {tech['context']}

---

📈 **Виральность: {virality['score']:.0f}%** {virality['level']}

---

🔮 **Эффект бабочки**

В ближайшие 6 месяцев технологию начнут внедрять в коммерческие продукты. Конкуренты представят аналоги.

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AINews #TechAnalysis #LLM"""
        
        return post

# ============================================================
# 6. ГЛАВНЫЙ АГЕНТ
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
        except:
            return False
    
    def run_cycle(self):
        print("="*70)
        print("🚀 FINAL NEWS AGENT - ЗАПУСК ЦИКЛА")
        print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("🌍 Перевод: английский → русский (MyMemory API)")
        print("="*70)
        
        # 1. Поиск новостей
        news_list = self.hunter.search_news(hours_back=6)
        
        if not news_list:
            print("\n❌ Новостей не найдено")
            return
        
        # 2. Оценка и фильтрация
        scored_news = []
        for news in news_list:
            virality = ViralityAnalyzer.analyze(news)
            news['virality'] = virality
            
            if self.db.is_published(news['url'], news['title']):
                print(f"   ⏭️ Уже публиковали: {news['title'][:40]}...")
                continue
            
            scored_news.append(news)
        
        scored_news.sort(key=lambda x: x['virality']['score'], reverse=True)
        best_news = scored_news[0] if scored_news else None
        
        if not best_news:
            print("\n❌ Нет новых новостей для публикации")
            return
        
        print(f"\n🏆 Топ-1 новость (виральность: {best_news['virality']['score']:.0f}%)")
        print(f"📰 {best_news['title'][:60]}...")
        print(f"🔗 {best_news['url']}")
        
        # 3. Парсим полную статью
        full_text = self.hunter.parse_full_article(best_news['url'])
        content_for_post = full_text if full_text else best_news['content']
        
        # 4. Форматируем и публикуем
        post = AICardiogram.format(
            title=best_news['title'],
            content=content_for_post,
            virality=best_news['virality']
        )
        
        if self.send_to_telegram(post):
            self.db.mark_published(best_news['url'], best_news['title'])
            print(f"\n✅ ОПУБЛИКОВАНО!")
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
