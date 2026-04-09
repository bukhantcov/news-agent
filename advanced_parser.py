from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
import json
import time
from datetime import datetime

class AdvancedPriceParser:
    """Продвинутый парсер с обходом блокировок"""
    
    def parse_with_selenium(self):
        """Парсинг с использованием браузера (обходит блокировки)"""
        print("🌐 Запуск браузера для парсинга...")
        
        # Настройка Chrome
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')  # Фоновый режим
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        try:
            # Автоматическая установка драйвера
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            
            # Открываем страницу
            driver.get('https://www.bitrix24.ru/prices/')
            
            # Ждем загрузки
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Ищем элементы с ценами
            page_text = driver.find_element(By.TAG_NAME, "body").text
            
            # Сохраняем скриншот (для отладки)
            driver.save_screenshot('bitrix24_prices.png')
            
            driver.quit()
            
            print("   ✅ Парсинг выполнен, скриншот сохранен")
            print("\n📝 Для извлечения точных цен нужно:")
            print("   1. Открыть bitrix24_prices.png")
            print("   2. Настроить конкретные CSS селекторы")
            
            return True
            
        except Exception as e:
            print(f"   ❌ Ошибка: {e}")
            print("   ⚠️ Возможно, нужен Chrome браузер")
            return False

if __name__ == "__main__":
    parser = AdvancedPriceParser()
    parser.parse_with_selenium()
