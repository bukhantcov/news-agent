import requests
import json
import os
import time
from datetime import datetime
from pathlib import Path
from full_article_parser import FullArticleParser

class FullNewsHunter:
    """Агент для сбора ПОЛНЫХ статей + генерации контента"""
    
    def __init__(self):
        self.article_parser = FullArticleParser()
        self.tavily_key = "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"
        
    def search_and_parse_full_articles(self, query, max_articles=5):
        """Поиск + парсинг полных статей"""
        
        print(f"\n🔍 Поиск: {query}")
        
        # 1. Поиск через Tavily
        url = "https://api.tavily.com/search"
        payload = {
            "query": query,
            "search_depth": "advanced",
            "max_results": max_articles
        }
        headers = {'Authorization': f'Bearer {self.tavily_key}', 'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, json=payload, headers=headers)
            if response.status_code != 200:
                print(f"   ❌ Ошибка API: {response.status_code}")
                return []
            
            results = response.json().get('results', [])
            print(f"   ✅ Найдено {len(results)} результатов")
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return []
        
        # 2. Парсим ПОЛНЫЕ статьи
        full_articles = []
        
        for i, result in enumerate(results, 1):
            print(f"\n   📰 Статья {i}/{len(results)}: {result.get('title', '')[:60]}...")
            
            # Парсим полный текст
            full_text = self.article_parser.get_full_article(
                result.get('url'), 
                result.get('source', '')
            )
            
            if full_text:
                # Сокращаем для соцсетей, но сохраняем полную версию
                short_text = self.article_parser.summarize_long_article(full_text, 2500)
                
                article_data = {
                    'title': result.get('title'),
                    'url': result.get('url'),
                    'source': result.get('source'),
                    'full_text': full_text,  # Полная версия
                    'short_text': short_text,  # Для соцсетей
                    'score': result.get('score', 0),
                    'content_preview': result.get('content', ''),
                    'parsed_at': datetime.now().isoformat()
                }
                full_articles.append(article_data)
                print(f"      ✅ Полный текст: {len(full_text)} символов")
            else:
                # Если не удалось распарсить, используем превью
                article_data = {
                    'title': result.get('title'),
                    'url': result.get('url'),
                    'source': result.get('source'),
                    'full_text': result.get('content', ''),
                    'short_text': result.get('content', ''),
                    'score': result.get('score', 0),
                    'content_preview': result.get('content', ''),
                    'parsed_at': datetime.now().isoformat(),
                    'note': 'Не удалось распарсить полный текст'
                }
                full_articles.append(article_data)
                print(f"      ⚠️ Только превью: {len(result.get('content', ''))} символов")
            
            time.sleep(2)  # Пауза между запросами
        
        return full_articles
    
    def create_rich_post(self, article, platform='telegram'):
        """Создание поста с полным содержанием"""
        
        if platform == 'telegram':
            # Telegram: используем сокращенную версию + ссылку
            post = f"""
🔥 **{article['title']}**

{article['short_text']}

━━━━━━━━━━━━━━━━━━━━━━
📊 *Источник:* {article['source']}
🔗 *Читать полностью:* {article['url']}
🕒 *Парсинг:* {article['parsed_at']}

#AI #Нейросети #Новости
"""
        elif platform == 'full_article':
            # Полная версия для архива
            post = f"""
{'='*70}
📰 {article['title']}
{'='*70}

Источник: {article['source']}
URL: {article['url']}
Дата парсинга: {article['parsed_at']}

{'='*70}
ПОЛНЫЙ ТЕКСТ СТАТЬИ:
{'='*70}

{article['full_text']}

{'='*70}
Конец статьи
{'='*70}
"""
        else:  # dzen
            post = f"""
<article>
<h1>{article['title']}</h1>
<p><i>Источник: {article['source']}</i></p>

{article['short_text'].replace(chr(10), '<br/>')}

<p><a href="{article['url']}">Читать полностью на источнике →</a></p>

<div class="tags">
#AI #Нейросети #Технологии
</div>
</article>
"""
        return post
    
    def save_full_articles(self, articles, folder_name=None):
        """Сохранение полных статей + постов"""
        
        if not folder_name:
            folder_name = f"full_news_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"
        
        os.makedirs(folder_name, exist_ok=True)
        os.makedirs(f"{folder_name}/full_articles", exist_ok=True)
        os.makedirs(f"{folder_name}/telegram", exist_ok=True)
        os.makedirs(f"{folder_name}/dzen", exist_ok=True)
        
        saved = []
        
        for i, article in enumerate(articles, 1):
            # Сохраняем ПОЛНУЮ статью в JSON
            full_json = f"{folder_name}/full_articles/article_{i}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(full_json, 'w', encoding='utf-8') as f:
                json.dump(article, f, ensure_ascii=False, indent=2)
            
            # Сохраняем полный текст как TXT
            full_txt = f"{folder_name}/full_articles/full_text_{i}.txt"
            with open(full_txt, 'w', encoding='utf-8') as f:
                f.write(self.create_rich_post(article, 'full_article'))
            
            # Telegram пост
            tg_post = self.create_rich_post(article, 'telegram')
            tg_file = f"{folder_name}/telegram/post_{i}.txt"
            with open(tg_file, 'w', encoding='utf-8') as f:
                f.write(tg_post)
            
            # Дзен статья
            dzen_post = self.create_rich_post(article, 'dzen')
            dzen_file = f"{folder_name}/dzen/article_{i}.html"
            with open(dzen_file, 'w', encoding='utf-8') as f:
                f.write(dzen_post)
            
            saved.append({
                'title': article['title'],
                'full_article': full_json,
                'full_text': full_txt,
                'telegram': tg_file,
                'dzen': dzen_file
            })
            
            print(f"   ✅ {article['title'][:50]}...")
        
        # Создаем сводку
        summary = f"""
{'='*70}
📊 СВОДКА ПОЛНЫХ СТАТЕЙ
{'='*70}
Дата: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
Всего статей: {len(articles)}
Полных текстов: {sum(1 for a in articles if len(a.get('full_text', '')) > 500)}

📁 Папка: {folder_name}/

{'='*70}
📚 СОХРАНЕНО:
• Полные статьи: {folder_name}/full_articles/
• Telegram посты: {folder_name}/telegram/
• Дзен статьи: {folder_name}/dzen/
{'='*70}
"""
        with open(f"{folder_name}/SUMMARY.txt", 'w', encoding='utf-8') as f:
            f.write(summary)
        
        print(f"\n💾 Сохранено в папку: {folder_name}/")
        return folder_name
    
    def run(self):
        """Запуск сбора ПОЛНЫХ статей"""
        
        print("="*70)
        print("📰 FULL NEWS HUNTER - Сбор ПОЛНЫХ статей")
        print("="*70)
        print(f"⏰ {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}")
        print("="*70)
        
        queries = [
            "искусственный интеллект новые технологии 2026",
            "нейросети прорыв сегодня",
            "AI новости искусственный интеллект"
        ]
        
        all_articles = []
        for query in queries:
            articles = self.search_and_parse_full_articles(query, max_articles=3)
            all_articles.extend(articles)
            time.sleep(3)
        
        # Удаляем дубликаты по URL
        unique_articles = []
        seen_urls = set()
        for article in all_articles:
            if article['url'] not in seen_urls:
                seen_urls.add(article['url'])
                unique_articles.append(article)
        
        print(f"\n📊 Уникальных статей: {len(unique_articles)}")
        print(f"   Из них с полным текстом: {sum(1 for a in unique_articles if len(a.get('full_text', '')) > 500)}")
        
        # Сохраняем всё
        folder = self.save_full_articles(unique_articles)
        
        print("\n✅ ГОТОВО!")
        return folder

if __name__ == "__main__":
    hunter = FullNewsHunter()
    hunter.run()
