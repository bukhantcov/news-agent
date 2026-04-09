import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime

class RealPriceParser:
    """Реальный парсер цен с сайтов"""
    
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }
        self.results = {}
    
    def parse_bitrix24(self):
        """Парсинг цен Битрикс24"""
        print("🌐 Парсинг https://www.bitrix24.ru/prices/...")
        
        try:
            response = requests.get(
                'https://www.bitrix24.ru/prices/', 
                headers=self.headers, 
                timeout=10
            )
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Ищем цены по разным паттернам
                prices = []
                
                # Паттерн 1: числа с рублями
                text = soup.get_text()
                price_patterns = re.findall(r'(\d+[\s\d]*)\s*₽', text)
                
                for price in price_patterns[:20]:  # Первые 20 цен
                    prices.append(price.strip() + " ₽")
                
                # Паттерн 2: поиск тарифных планов
                tariff_blocks = soup.find_all(class_=re.compile(r'tariff|price|plan', re.I))
                
                self.results['bitrix24'] = {
                    'url': 'https://www.bitrix24.ru/prices/',
                    'prices_found': prices if prices else ['Не удалось распарсить цены'],
                    'timestamp': datetime.now().isoformat(),
                    'note': 'Данные получены автоматическим парсингом'
                }
                
                print(f"   ✅ Найдено {len(prices)} ценовых предложений")
                return True
            else:
                print(f"   ❌ Ошибка HTTP {response.status_code}")
                return False
                
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            return False
    
    def search_via_google(self, query):
        """Поиск через Google (требует API)"""
        print(f"🔍 Поиск: {query}")
        print("   ⚠️ Для реального поиска нужен SerpAPI ключ")
        print("   Получите бесплатный ключ: https://serpapi.com/")
        return None
    
    def save_results(self):
        """Сохранение результатов"""
        filename = f"parsed_prices_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)
        print(f"\n💾 Результаты сохранены в {filename}")
        return filename

def main():
    print("="*60)
    print("🤖 РЕАЛЬНЫЙ AI-АГЕНТ ПАРСЕР ЦЕН")
    print("="*60)
    print("\n⚠️ Важно: Некоторые сайты могут блокировать парсинг")
    print("   Для обхода нужны прокси или API\n")
    
    parser = RealPriceParser()
    
    # Парсинг Битрикс24
    parser.parse_bitrix24()
    
    # Вывод результатов
    print("\n" + "="*60)
    print("📊 РЕЗУЛЬТАТЫ ПАРСИНГА")
    print("="*60)
    
    if 'bitrix24' in parser.results:
        print("\n🏢 БИТРИКС24:")
        print(f"   Источник: {parser.results['bitrix24']['url']}")
        print(f"   Время: {parser.results['bitrix24']['timestamp']}")
        print("\n   Найденные цены:")
        for i, price in enumerate(parser.results['bitrix24']['prices_found'][:10], 1):
            print(f"   {i}. {price}")
    
    # Сохранение
    parser.save_results()
    
    # Инструкция по улучшению
    print("\n" + "="*60)
    print("🚀 КАК УЛУЧШИТЬ AI-АГЕНТА?")
    print("="*60)
    print("""
1. ДЛЯ ТОЧНОГО ПАРСИНГА:
   • Используйте Selenium (для динамических сайтов)
   • Подключите прокси (чтобы не блокировали IP)
   • Настройте регулярные обновления (cron)

2. ДЛЯ ПОИСКА КОНКУРЕНТОВ:
   • SerpAPI (первые 100 запросов бесплатно)
   • Google Custom Search API

3. ДЛЯ AI-АНАЛИЗА:
   • OpenAI API для анализа тональности
   • Кластеризация найденных данных

Хотите настроить полноценного агента? 
Напишите 'да' и я помогу с API ключами!
    """)

if __name__ == "__main__":
    main()
