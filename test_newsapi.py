import requests
import json

API_KEY = "e08eafb22acc4ad983888ecbcdb492d4"

# Простой запрос
url = "https://newsapi.org/v2/everything"
params = {
    'q': 'artificial intelligence',
    'language': 'en',
    'sortBy': 'publishedAt',
    'pageSize': 5,
    'apiKey': API_KEY
}

print("🔍 Тест NewsAPI...")
print(f"Запрос: {params['q']}")

try:
    response = requests.get(url, params=params, timeout=30)
    data = response.json()
    
    print(f"Статус: {data.get('status')}")
    print(f"Всего найдено: {data.get('totalResults', 0)}")
    
    if data.get('status') == 'ok':
        articles = data.get('articles', [])
        print(f"\n📰 Получено статей: {len(articles)}")
        
        for i, article in enumerate(articles[:3], 1):
            print(f"\n{i}. {article.get('title', '')[:60]}")
            print(f"   {article.get('description', '')[:80]}...")
    else:
        print(f"Ошибка: {data.get('message', 'Unknown')}")
        
except Exception as e:
    print(f"❌ Ошибка: {e}")
