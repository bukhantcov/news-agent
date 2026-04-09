#!/bin/bash

# Переход в директорию проекта
cd "/Users/denisbuhancov/Downloads/Проекты /AI-Agent-Competitive-Intelligence"

# Активация виртуального окружения
source venv/bin/activate

echo "=========================================="
echo "🤖 НОВОСТНОЙ БОТ - ЗАПУСК"
echo "=========================================="
echo "📁 Директория: $(pwd)"
echo ""

# Проверяем наличие файлов с новостями
NEWS_COUNT=$(find . -maxdepth 2 -name "*.txt" -type f | grep -v "posted_" | grep -v "requirements" | wc -l)

if [ "$NEWS_COUNT" -eq 0 ]; then
    echo "❌ Нет файлов с новостями!"
    echo "📡 Запускаю сбор новостей..."
    python3 real_news_agent.py
    echo ""
fi

# Публикуем новость
echo "📢 Публикация новости..."
python3 professional_news_template.py --once

echo ""
echo "✅ Готово!"
echo "=========================================="
