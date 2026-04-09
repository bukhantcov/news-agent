import requests
import re
import json
import time
import os
import glob
import hashlib
import random
from datetime import datetime

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class ExpertNewsAnalyst:
    """Экспертный AI-аналитик для обработки новостей"""
    
    # Критерии технологического прорыва
    TECH_KEYWORDS = {
        'architecture': ['MoE', 'Mixture of Experts', 'Transformer', 'Diffusion', 'Mamba', 'SSM'],
        'optimization': ['квантование', 'quantization', 'pruning', 'distillation', 'flash attention'],
        'benchmarks': ['MMLU', 'GSM8K', 'HumanEval', 'SWE-bench', 'LMSYS', 'arena'],
        'weights': ['веса', 'параметры', 'parameters', 'billion', 'миллиардов'],
        'efficiency': ['inference', 'token/s', 'TPS', 'задержка', 'latency', 'cost per token']
    }
    
    # Маркетинговый шум для удаления
    MARKETING_NOISE = [
        r'невероятн[ыо]й?', r'революционн[ыо]й?', r'потрясающ[и]й?',
        r'сенсационн[ыо]й?', r'уникальн[ыо]й?', r'прорывн[оы]й?',
        r'[Бб]еспрецедентн[ыо]й?', r'[Вв]елликолепн[ыо]й?', r'[Ии]зумительн[ыо]й?'
    ]
    
    @staticmethod
    def filter_news(content):
        """Жесткая фильтрация новостей"""
        content_lower = content.lower()
        
        # ❌ Исключаем маркетинговый шум без конкретики
        marketing_count = sum(1 for pattern in ExpertNewsAnalyst.MARKETING_NOISE if re.search(pattern, content_lower))
        if marketing_count > 3 and not any(kw in content_lower for kw in ['%', 'x', 'раз', 'млн', 'млрд']):
            return False, "Маркетинговый шум без цифр"
        
        # ✅ Должен быть технический контент
        has_tech = False
        for category, keywords in ExpertNewsAnalyst.TECH_KEYWORDS.items():
            if any(kw.lower() in content_lower for kw in keywords):
                has_tech = True
                break
        
        if not has_tech:
            return False, "Нет технических деталей"
        
        # ✅ Должны быть цифры или конкретные данные
        has_numbers = bool(re.search(r'\d+[\s]*[%x]?', content))
        if not has_numbers:
            return False, "Нет цифр и данных"
        
        # ✅ Должен быть источник или конкретика
        has_source = bool(re.search(r'github|arxiv|paper|research|openai|google|meta|microsoft', content_lower))
        
        return True, "OK"
    
    @staticmethod
    def extract_tech_stack(content):
        """Извлечение технического стека"""
        tech_stack = {
            'architecture': 'Не указана',
            'parameters': 'Не раскрыто',
            'efficiency': 'Не указано',
            'context': 'Не указан'
        }
        
        # Архитектура
        for arch in ExpertNewsAnalyst.TECH_KEYWORDS['architecture']:
            if arch.lower() in content.lower():
                tech_stack['architecture'] = arch
                break
        
        # Параметры
        param_patterns = [
            r'(\d+(?:\.\d+)?)\s*[Bb]',
            r'(\d+(?:\.\d+)?)\s*миллиард',
            r'(\d+(?:\.\d+)?)\s*млрд',
        ]
        for pattern in param_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                tech_stack['parameters'] = f"{match.group(1)}B"
                break
        
        # Контекстное окно
        context_match = re.search(r'(\d+(?:\.\d+)?)\s*[KkMm]?\s*токен', content, re.IGNORECASE)
        if context_match:
            tech_stack['context'] = f"{context_match.group(0)}"
        
        return tech_stack
    
    @staticmethod
    def analyze_impact(content):
        """Анализ влияния на разные сферы"""
        content_lower = content.lower()
        
        impacts = {}
        
        # Для разработчиков
        if any(kw in content_lower for kw in ['api', 'sdk', 'open source', 'github']):
            impacts['developers'] = {'score': 8, 'reason': 'Доступно для интеграции'}
        elif any(kw in content_lower for kw in ['бесплатно', 'локально']):
            impacts['developers'] = {'score': 7, 'reason': 'Низкий порог входа'}
        else:
            impacts['developers'] = {'score': 5, 'reason': 'Требуется изучение'}
        
        # Для бизнеса
        if any(kw in content_lower for kw in ['экономия', 'cost', 'дешевле', 'быстрее']):
            impacts['business'] = {'score': 9, 'reason': 'Прямая экономия ресурсов'}
        elif any(kw in content_lower for kw in ['api', 'cloud', 'облако']):
            impacts['business'] = {'score': 7, 'reason': 'Готовая инфраструктура'}
        else:
            impacts['business'] = {'score': 4, 'reason': 'ROI требует оценки'}
        
        # Для обывателей
        if any(kw in content_lower for kw in ['app', 'ios', 'android', 'приложение']):
            impacts['users'] = {'score': 8, 'reason': 'Уже в магазинах приложений'}
        else:
            impacts['users'] = {'score': 3, 'reason': 'Пока для специалистов'}
        
        return impacts
    
    @staticmethod
    def generate_forecast(title, content, tech_stack):
        """Экспертный прогноз на рынок"""
        content_lower = content.lower()
        
        forecast_templates = []
        
        # Прогноз на основе типа новости
        if 'open source' in content_lower or 'github' in content_lower:
            forecast_templates.append(
                "В течение 3-6 месяцев ждем форк-решения от крупных вендоров. "
                "Open-source реализация станет базой для корпоративных продуктов, "
                "что снизит TCO на 40-60% для компаний, внедряющих AI."
            )
        
        if 'api' in content_lower or 'cloud' in content_lower:
            forecast_templates.append(
                "API-экономика ускорится: появятся агрегаторы и обертки. "
                "Цены на токены снизятся на 20-30% из-за конкуренции. "
                "Разработчики смогут собирать сложные пайплайны за дни, а не месяцы."
            )
        
        if tech_stack['parameters'] != 'Не раскрыто':
            forecast_templates.append(
                f"С {tech_stack['parameters']} параметров модель войдет в топ-10 по соотношению "
                "цена/качество. Ожидаем появление optimized версий для edge-устройств в течение полугода."
            )
        
        if not forecast_templates:
            forecast_templates.append(
                "Технология вызовет волну подражаний. Крупные игроки представят "
                "аналоги в течение 2-3 месяцев. Рынок MLOps получит новый стандарт."
            )
        
        return random.choice(forecast_templates)
    
    @staticmethod
    def create_expert_post(title, content):
        """Создание экспертного поста"""
        
        # Очистка от маркетингового шума
        clean_content = content
        for pattern in ExpertNewsAnalyst.MARKETING_NOISE:
            clean_content = re.sub(pattern, '', clean_content, flags=re.IGNORECASE)
        
        # Извлечение технического стека
        tech_stack = ExpertNewsAnalyst.extract_tech_stack(clean_content)
        
        # Анализ влияния
        impacts = ExpertNewsAnalyst.analyze_impact(clean_content)
        
        # Прогноз
        forecast = ExpertNewsAnalyst.generate_forecast(title, clean_content, tech_stack)
        
        # Формирование поста
        post = f"""⚡️ **{title[:80]}**

📅 Статус: 🟢 РЕЛИЗ / OPENSOURCE

---

🧠 **Техно-стек**

`Архитектура:` {tech_stack['architecture']}
`Параметры:` {tech_stack['parameters']}
`Контекст:` {tech_stack['context']}

---

⚙️ **Ключевые метрики**

{ExpertNewsAnalyst.extract_key_metrics(clean_content)}

---

📈 **Индекс влияния**

| Сфера | Оценка | Обоснование |
|-------|--------|-------------|
| 👨‍💻 Разработчики | ⚡️ {impacts['developers']['score']}/10 | {impacts['developers']['reason']} |
| 💼 Бизнес | 💰 {impacts['business']['score']}/10 | {impacts['business']['reason']} |
| 🌍 Рынок | 📊 7/10 | Меняет конкурентный ландшафт |

---

🔮 **Эффект бабочки**

{forecast}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AINews #TechAnalysis #LLM"""
        
        return post
    
    @staticmethod
    def extract_key_metrics(content):
        """Извлечение ключевых метрик"""
        metrics = []
        
        # Ищем проценты
        percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', content)
        if percentages:
            metrics.append(f"• Улучшение: +{percentages[0]}%")
        
        # Ищем ускорение
        speed = re.findall(r'(\d+(?:\.\d+)?)\s*[хx]', content)
        if speed:
            metrics.append(f"• Ускорение: {speed[0]}x")
        
        # Ищем стоимость
        cost = re.findall(r'(\d+(?:\.\d+)?)\s*[$₽]', content)
        if cost:
            metrics.append(f"• Стоимость: {cost[0]}")
        
        if not metrics:
            metrics = ["• Данные в процессе анализа"]
        
        return '\n'.join(metrics[:3])


class ExpertPoster:
    def __init__(self):
        self.db_file = "expert_posted_db.json"
        self.load_db()
    
    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'hashes': []}
    
    def save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def find_news(self):
        """Поиск новостей для анализа"""
        news_files = []
        
        for pattern in ["**/*.txt", "**/post_*.txt", "**/news_*.txt"]:
            found = glob.glob(pattern, recursive=True)
            found = [f for f in found if 'venv' not in f and 'posted_' not in f]
            news_files.extend(found)
        
        news_files = list(set(news_files))
        news_files.sort(key=os.path.getctime, reverse=True)
        
        for file_path in news_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                if len(content) < 400:
                    continue
                
                # Проверка на дубликат
                content_hash = hashlib.md5(content[:300].encode()).hexdigest()
                if content_hash in self.db['hashes']:
                    continue
                
                # Экспертная фильтрация
                is_valid, reason = ExpertNewsAnalyst.filter_news(content)
                if not is_valid:
                    print(f"   ⏭️ {os.path.basename(file_path)} - {reason}")
                    continue
                
                # Извлечение заголовка
                title = ""
                lines = content.split('\n')
                for line in lines[:10]:
                    line = line.strip()
                    if 20 < len(line) < 120 and not line.startswith('http'):
                        title = line
                        break
                
                if not title:
                    title = content[:80]
                
                return file_path, title, content
                
            except Exception as e:
                continue
        
        return None, None, None
    
    def send_message(self, text):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {'chat_id': CHANNEL_ID, 'text': text}
        
        try:
            r = requests.post(url, json=payload, timeout=30)
            return r.status_code == 200
        except Exception as e:
            print(f"   ❌ {e}")
            return False
    
    def post_one(self):
        print(f"\n🔍 Экспертный анализ новостей...")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        file_path, title, content = self.find_news()
        
        if not file_path:
            print("\n❌ Нет технических новостей с конкретикой")
            print("💡 Критерии: архитектура + цифры + практическая применимость")
            return False
        
        print(f"\n📰 Источник: {os.path.basename(file_path)}")
        print(f"📝 Анализ: {title[:60]}...")
        
        post = ExpertNewsAnalyst.create_expert_post(title, content)
        
        if len(post) > 4096:
            post = post[:4093] + "..."
        
        if self.send_message(post):
            content_hash = hashlib.md5(content[:300].encode()).hexdigest()
            self.db['hashes'].append(content_hash)
            self.save_db()
            print(f"\n✅ Экспертный анализ опубликован!")
            return True
        else:
            print(f"\n❌ Ошибка публикации")
            return False
    
    def run_once(self):
        self.post_one()


if __name__ == "__main__":
    poster = ExpertPoster()
    poster.run_once()
