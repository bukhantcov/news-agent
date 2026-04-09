#!/bin/bash

cd "/Users/denisbuhancov/Downloads/Проекты /AI-Agent-Competitive-Intelligence"
source venv/bin/activate

echo "🚀 $(date): Запуск сбора новостей" >> logs/full_cycle.log

# Сбор новостей
python3 real_news_agent.py >> logs/full_cycle.log 2>&1

# Пауза
sleep 10

# Постинг в Telegram
python3 tg_auto_post.py >> logs/full_cycle.log 2>&1

echo "✅ $(date): Цикл завершен" >> logs/full_cycle.log
