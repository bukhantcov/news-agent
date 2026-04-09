#!/bin/bash

cd "/Users/denisbuhancov/Downloads/Проекты /AI-Agent-Competitive-Intelligence"
source venv/bin/activate

echo "🚀 Запуск часового постинга"
echo "📅 $(date)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

python3 humanizer_and_poster.py --hourly
