import requests
import re
import json
import time
import os
import glob
import hashlib
from datetime import datetime

BOT_TOKEN = "8738939654:AAEhLC_6dk4IxwurgadWMWXXoGcE1DXRE9o"
CHANNEL_ID = "@DenisBukhancov_CRM_AI"

class QualityGateKeeper:
    """Контроль качества - пропускаем только реально ценные новости"""
    
    # Технические поля, которые должны быть заполнены
    TECH_FIELDS = [
        'architecture',   # архитектура (MoE, Transformer, Diffusion)
        'parameters',     # количество параметров (70B, 405B)
        'context',        # контекстное окно (128K, 1M tokens)
        'efficiency',     # эффективность (токен/сек, задержка)
        'cost',          # стоимость ($0.01/1K tokens)
        'benchmark'      # результаты бенчмарков (MMLU, GSM8K)
    ]
    
    @staticmethod
    def extract_tech_details(content):
        """Извлечение технических деталей из текста"""
        details = {}
        content_lower = content.lower()
        
        # Архитектура
        architectures = {
            'MoE': ['moe', 'mixture of experts', 'экспертов'],
            'Transformer': ['transformer', 'attention'],
            'Diffusion': ['diffusion', 'denoising'],
            'Mamba': ['mamba', 'ssm', 'state space'],
            'CNN': ['cnn', 'convolutional'],
        }
        
        for arch, keywords in architectures.items():
            if any(kw in content_lower for kw in keywords):
                details['architecture'] = arch
                break
        else:
            details['architecture'] = None
        
        # Параметры
        param_patterns = [
            (r'(\d+(?:\.\d+)?)\s*[Bb](?!\w)', 'B'),
            (r'(\d+(?:\.\d+)?)\s*миллиард', 'B'),
            (r'(\d+(?:\.\d+)?)\s*млрд', 'B'),
            (r'(\d+(?:\.\d+)?)\s*[Mm](?!\w)', 'M'),
            (r'(\d+(?:\.\d+)?)\s*миллион', 'M'),
        ]
        
        params = None
        for pattern, suffix in param_patterns:
            match = re.search(pattern, content, re.IGNORECASE)
            if match:
                params = f"{match.group(1)}{suffix}"
                break
        details['parameters'] = params
        
        # Контекстное окно
        context_match = re.search(r'(\d+(?:\.\d+)?)\s*([KkMm]?)\s*токен', content, re.IGNORECASE)
        if context_match:
            val = context_match.group(1)
            unit = context_match.group(2).upper() if context_match.group(2) else ''
            details['context'] = f"{val}{unit} tokens"
        else:
            details['context'] = None
        
        # Эффективность (токен/сек, задержка)
        efficiency_match = re.search(r'(\d+(?:\.\d+)?)\s*(токен/с|t/s|tok/s|ms|сек)', content, re.IGNORECASE)
        if efficiency_match:
            details['efficiency'] = efficiency_match.group(0)
        else:
            details['efficiency'] = None
        
        # Стоимость
        cost_match = re.search(r'[$₽]\s*(\d+(?:\.\d+)?)', content)
        if cost_match:
            details['cost'] = f"${cost_match.group(1)}"
        else:
            details['cost'] = None
        
        # Бенчмарки
        benchmarks = ['MMLU', 'GSM8K', 'HumanEval', 'SWE-bench', 'LMSYS', 'HellaSwag']
        found_benchmarks = [b for b in benchmarks if b.lower() in content_lower]
        details['benchmark'] = found_benchmarks[0] if found_benchmarks else None
        
        return details
    
    @staticmethod
    def calculate_quality_score(details):
        """Расчет оценки качества новости (0-100)"""
        filled_fields = sum(1 for v in details.values() if v is not None)
        score = (filled_fields / len(QualityGateKeeper.TECH_FIELDS)) * 100
        
        # Бонус за конкретные цифры
        if details.get('parameters') and 'B' in str(details['parameters']):
            score += 10
        if details.get('context') and 'M' in str(details['context']):
            score += 10
        if details.get('benchmark'):
            score += 15
        
        return min(score, 100)
    
    @staticmethod
    def should_post(content, title):
        """Решение: публиковать или пропустить"""
        
        # Проверка на пустышку
        if '?' in title and len(title) < 50:
            return False, "Вопросительный заголовок-пустышка"
        
        if 'прорывы в области ИИ' in content.lower():
            return False, "Общая фраза без конкретики"
        
        if 'QZY' in content or 'Cust' in content:
            return False, "Рекламный мусор"
        
        # Извлекаем технические детали
        details = QualityGateKeeper.extract_tech_details(content)
        quality_score = QualityGateKeeper.calculate_quality_score(details)
        
        print(f"   📊 Технических полей заполнено: {sum(1 for v in details.values() if v)}/{len(QualityGateKeeper.TECH_FIELDS)}")
        print(f"   📈 Quality Score: {quality_score:.0f}%")
        
        # Порог качества: минимум 40% (хотя бы 2-3 поля)
        if quality_score < 40:
            return False, f"Низкое качество ({quality_score:.0f}%)"
        
        # Дополнительная проверка: должна быть хоть одна конкретная цифра
        has_numbers = bool(re.search(r'\d+', content))
        if not has_numbers:
            return False, "Нет цифр и конкретных данных"
        
        return True, f"OK ({quality_score:.0f}%)"
    
    @staticmethod
    def create_quality_post(title, content, details, quality_score):
        """Создание поста только из реальных данных"""
        
        # Заполняем только те поля, где есть данные
        tech_stack_lines = []
        if details.get('architecture'):
            tech_stack_lines.append(f"`Архитектура:` {details['architecture']}")
        if details.get('parameters'):
            tech_stack_lines.append(f"`Параметры:` {details['parameters']}")
        if details.get('context'):
            tech_stack_lines.append(f"`Контекст:` {details['context']}")
        if details.get('efficiency'):
            tech_stack_lines.append(f"`Производительность:` {details['efficiency']}")
        if details.get('cost'):
            tech_stack_lines.append(f"`Стоимость:` {details['cost']}")
        
        tech_stack = '\n'.join(tech_stack_lines) if tech_stack_lines else "`Данные не раскрыты`"
        
        # Извлекаем ключевые цифры
        metrics = []
        numbers = re.findall(r'(\d+(?:\.\d+)?)\s*(%|[хx]|раз|токен|ms|с)', content)
        for num, unit in numbers[:3]:
            metrics.append(f"• {num}{unit}")
        
        metrics_text = '\n'.join(metrics) if metrics else "• Подробности в источнике"
        
        # Берем суть (первые 2-3 предложения без воды)
        sentences = re.split(r'[.!?]+', content)
        core = []
        for s in sentences[:3]:
            s = s.strip()
            if 30 < len(s) < 250 and '?' not in s and not s.startswith('Как'):
                core.append(s)
        
        essence = '. '.join(core)[:400]
        
        post = f"""⚡️ **{title[:80]}**

📅 Статус: 🟢 ТЕХНИЧЕСКИЙ РЕЛИЗ

---

🧠 **Технические характеристики**

{tech_stack}

---

📊 **Ключевые метрики**

{metrics_text}

---

📈 **Оценка качества: {quality_score:.0f}%** {"🔥" * (int(quality_score/20))}

---

📌 @DenisBukhancov_CRM_AI
📅 {datetime.now().strftime('%d.%m.%Y | %H:%M')}
#AINews #TechAnalysis #LLM"""
        
        return post


class QualityPoster:
    def __init__(self):
        self.db_file = "quality_posted_db.json"
        self.load_db()
    
    def load_db(self):
        if os.path.exists(self.db_file):
            with open(self.db_file, 'r') as f:
                self.db = json.load(f)
        else:
            self.db = {'hashes': [], 'titles': []}
    
    def save_db(self):
        with open(self.db_file, 'w') as f:
            json.dump(self.db, f, indent=2)
    
    def find_news(self):
        """Поиск новостей с качественным контентом"""
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
                
                # Извлекаем заголовок
                title = ""
                lines = content.split('\n')
                for line in lines[:10]:
                    line = line.strip()
                    if 20 < len(line) < 120 and not line.startswith('http'):
                        title = line
                        break
                
                if not title:
                    title = content[:80]
                
                # Проверка на дубликат
                content_hash = hashlib.md5(content[:300].encode()).hexdigest()
                if content_hash in self.db['hashes']:
                    continue
                
                # Контроль качества
                should, reason = QualityGateKeeper.should_post(content, title)
                
                if should:
                    print(f"   ✅ {os.path.basename(file_path)} - {reason}")
                    return file_path, title, content
                else:
                    print(f"   ⏭️ {os.path.basename(file_path)} - {reason}")
                    continue
                
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
        print(f"\n🔍 Контроль качества новостей...")
        print(f"⏰ {datetime.now().strftime('%H:%M:%S')}")
        
        file_path, title, content = self.find_news()
        
        if not file_path:
            print("\n❌ Нет новостей, прошедших контроль качества")
            print("💡 Лучше пропустить час, чем выдать пустышку")
            return False
        
        # Извлекаем детали для поста
        details = QualityGateKeeper.extract_tech_details(content)
        quality_score = QualityGateKeeper.calculate_quality_score(details)
        
        post = QualityGateKeeper.create_quality_post(title, content, details, quality_score)
        
        if self.send_message(post):
            content_hash = hashlib.md5(content[:300].encode()).hexdigest()
            self.db['hashes'].append(content_hash)
            self.save_db()
            print(f"\n✅ Качественная новость опубликована! (Score: {quality_score:.0f}%)")
            return True
        else:
            print(f"\n❌ Ошибка публикации")
            return False
    
    def run_once(self):
        self.post_one()


if __name__ == "__main__":
    poster = QualityPoster()
    poster.run_once()
