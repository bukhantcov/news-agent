#!/bin/bash

cd "/Users/denisbuhancov/Downloads/Проекты /AI-Agent-Competitive-Intelligence"
source venv/bin/activate

echo "🚀 ЗАПУСК УМНОГО ПОСТИНГА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ 1 новость в час"
echo "✅ Проверка на дубликаты"
echo "✅ Уникальное оформление"
echo "✅ Только качественные новости"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 smart_hourly_poster.py --hourly
