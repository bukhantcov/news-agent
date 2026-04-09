import os
import requests
import sys

def main():
    print("="*50)
    print("🧪 TELEGRAM TEST AGENT")
    print("="*50)
    
    # Получаем токен из секретов GitHub
    bot_token = os.environ.get("BOT_TOKEN")
    channel_id = "@DenisBukhancov_CRM_AI"
    
    if not bot_token:
        print("❌ Ошибка: BOT_TOKEN не найден в переменных окружения")
        sys.exit(1)
    
    print(f"✅ BOT_TOKEN найден (первые 5 символов: {bot_token[:5]}...)")
    print(f"📢 Канал: {channel_id}")
    
    # Пробуем отправить сообщение
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        'chat_id': channel_id,
        'text': '✅ *Тест GitHub Actions!*\n\nБот успешно запустился и работает.',
        'parse_mode': 'Markdown'
    }
    
    try:
        response = requests.post(url, json=payload, timeout=30)
        print(f"📤 Статус ответа Telegram API: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Сообщение успешно отправлено в Telegram!")
            print("🎉 Тест пройден! Проблема была в GigaChat, а не в боте или GitHub.")
            sys.exit(0)
        else:
            print(f"❌ Ошибка Telegram API: {response.text}")
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Исключение при отправке: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
