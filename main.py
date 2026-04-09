import os
import sys
import json
import requests
from datetime import datetime
from typing import Dict, List, Optional
import re

def get_current_data(competitor: str) -> Dict:
    """
    Здесь вы можете вручную обновить актуальные данные
    Проверьте официальные сайты для получения актуальной информации
    """
    
    # АКТУАЛЬНЫЕ ДАННЫЕ НА 2026 ГОД
    # ⚠️ ПРОВЕРЬТЕ ОФИЦИАЛЬНЫЕ САЙТЫ ДЛЯ ОБНОВЛЕНИЯ:
    # https://www.bitrix24.ru/prices/
    # https://www.amocrm.ru/tariffs/
    
    data_db = {
        "Битрикс24": {
            "company": "Битрикс24",
            "parent_company": "1С-Битрикс",
            "founded": "2012",
            "headquarters": "Россия, Москва",
            "employees": "1500+",
            "market_position": "Лидер на рынке CRM в России и СНГ",
            "pricing_2026": {
                "free": "До 15 сотрудников бесплатно",
                "basic": "от 1990 ₽/мес",
                "standard": "от 3990 ₽/мес",
                "professional": "от 7990 ₽/мес",
                "enterprise": "Индивидуально (от 19990 ₽/мес)"
            },
            "new_features_2026": [
                "Нейросеть Битрикс24.AI",
                "Автоматическое заполнение карточек сделок",
                "Распознавание речи в звонках",
                "Чат-боты на базе GPT"
            ]
        },
        "AmoCRM": {
            "company": "AmoCRM",
            "pricing_2026": {
                "free": "14 дней триал",
                "basic": "от 1499 ₽/мес",
                "advanced": "от 2999 ₽/мес",
                "enterprise": "от 5999 ₽/мес"
            }
        },
        "Salesforce": {
            "company": "Salesforce",
            "pricing_2026": {
                "starter": "$25/мес",
                "professional": "$75/мес",
                "enterprise": "$150/мес",
                "unlimited": "$300/мес"
            }
        }
    }
    
    # Ищем данные по конкуренту
    for key in data_db:
        if key.lower() in competitor.lower():
            return data_db[key]
    
    return data_db.get("Битрикс24", {})

def update_from_url() -> bool:
    """Функция для обновления данных с API или сайта"""
    print("⚠️ Для получения актуальных данных посетите:")
    print("   • Битрикс24: https://www.bitrix24.ru/prices/")
    print("   • AmoCRM: https://www.amocrm.ru/tariffs/")
    print("   • Salesforce: https://www.salesforce.com/pricing/")
    return False

def generate_detailed_report(niche: str, competitor: str) -> str:
    """Генерация отчета с актуальными данными"""
    
    # Здесь вы можете вручную ввести актуальные данные
    print("\n📝 Для актуальных данных заполните информацию:")
    print("-" * 50)
    
    # Интерактивный ввод данных
    use_manual = input("Хотите ввести актуальные данные вручную? (да/нет): ").strip().lower()
    
    if use_manual == "да":
        print("\nВведите актуальные данные для", competitor)
        pricing = {}
        pricing['free'] = input("Бесплатный тариф: ") or "Уточните на сайте"
        pricing['basic'] = input("Базовый тариф: ") or "Уточните на сайте"
        pricing['business'] = input("Бизнес тариф: ") or "Уточните на сайте"
        pricing['enterprise'] = input("Enterprise тариф: ") or "Уточните на сайте"
        
        report = f"""
{'='*60}
  АНАЛИЗ КОНКУРЕНТНОЙ РАЗВЕДКИ
  Актуальные данные на {datetime.now().strftime('%d.%m.%Y')}
{'='*60}

Ниша анализа: {niche}
Конкурент: {competitor}

💰 АКТУАЛЬНЫЕ ТАРИФЫ ({datetime.now().strftime('%B %Y')}):

• Бесплатный: {pricing['free']}
• Базовый: {pricing['basic']}
• Бизнес: {pricing['business']}
• Enterprise: {pricing['enterprise']}

⚠️ Важно: Данные введены вручную. 
Рекомендуется проверить актуальность на официальном сайте.

📌 Следующие шаги:
1. Посетите официальный сайт {competitor}
2. Проверьте раздел "Тарифы" или "Pricing"
3. Обновите данные в этом отчете

{'='*60}
"""
    else:
        # Используем базовые данные с указанием проверить
        report = f"""
{'='*60}
  АНАЛИЗ КОНКУРЕНТНОЙ РАЗВЕДКИ
{'='*60}

Ниша: {niche}
Конкурент: {competitor}
Дата анализа: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}

⚠️ ВНИМАНИЕ: Данные требуют обновления!

Для получения актуальной информации на 2026 год:

1️⃣ Битрикс24:
   → https://www.bitrix24.ru/prices/
   • Бесплатно: до 15 сотрудников
   • Базовый: проверьте на сайте
   • Стандарт: проверьте на сайте

2️⃣ AmoCRM:
   → https://www.amocrm.ru/tariffs/

3️⃣ Salesforce:
   → https://www.salesforce.com/pricing/

📝 Инструкция по обновлению данных:
1. Откройте main.py
2. Найдите функцию get_current_data()
3. Обновите словарь pricing_2026 актуальными значениями
4. Сохраните файл и запустите заново

📊 Рекомендации:
• Подпишитесь на рассылку обновлений конкурентов
• Настройте мониторинг цен через парсинг сайтов
• Проверяйте тарифы ежемесячно

{'='*60}
"""
    
    return report

def main():
    print("🚀 AI Agent Competitive Intelligence System v2.0")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        niche = sys.argv[1]
        competitor = sys.argv[2] if len(sys.argv) > 2 else input("Введите конкурента: ")
    else:
        niche = input("📌 Введите нишу (например: CRM, E-commerce): ").strip()
        competitor = input("🏢 Введите конкурента для анализа: ").strip()
    
    print(f"\n🔍 Анализ для: {competitor}")
    print("⏳ Подготовка отчета...\n")
    
    # Генерация отчета
    report = generate_detailed_report(niche, competitor)
    
    # Сохранение
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"report_{competitor.replace(' ', '_')}_{timestamp}.txt"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(report)
    
    print(f"✅ Отчет сохранен: {filename}")
    print("\n" + report)

if __name__ == "__main__":
    main()
