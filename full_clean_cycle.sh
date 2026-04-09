#!/bin/bash

cd "/Users/denisbuhancov/Downloads/Проекты /AI-Agent-Competitive-Intelligence"
source venv/bin/activate

echo "🚀 $(date): Запуск цикла" >> logs/clean_cycle.log

# Сбор новостей
python3 real_news_agent.py >> logs/clean_cycle.log 2>&1

sleep 5

# Чистый постинг в Telegram
python3 tg_clean_poster.py >> logs/clean_cycle.log 2>&1

echo "✅ $(date): Цикл завершен" >> logs/clean_cycle.log
