import json
import requests
import io
import base64
import os
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

class AlemEngine:
    def __init__(self):
        self.gpt_url = "https://llm.alem.ai/v1/chat/completions"
        self.img_url = "https://llm.alem.ai/v1/images/generations"
        self.stt_url = "https://llm.alem.ai/v1/audio/transcriptions"
        
        self.gpt_headers = {"Authorization": f"Bearer {os.getenv('ALEM_GPT_KEY')}", "Content-Type": "application/json"}
        self.img_headers = {"Authorization": f"Bearer {os.getenv('ALEM_QWEN_KEY')}", "Content-Type": "application/json"}
        self.stt_headers = {"Authorization": f"Bearer {os.getenv('ALEM_STT_KEY')}"}

    def transcribe_audio(self, file_path):
        print("🎙 [STT] Аудио мәтінге аударылуда...")
        try:
            with open(file_path, "rb") as f:
                res = requests.post(
                    self.stt_url, headers=self.stt_headers, files={"file": f}, data={"model": "speech-to-text-kk"}
                ).json()
                return res.get("text", "")
        except Exception as e: return None

    def analyze_competitor_image(self, base64_image):
        print("👁️ [Vision] Шаблон құрылымы талдануда...")
        prompt = """
        Сен - элитный AI-Дизайнерсің. Мына Инстаграм постының дизайнын талда.
        Маған ТЕК ҚАНА JSON қайтар. JSON құрылымы:
        {
            "suggested_topic": "Посттың негізгі тақырыбы қазақша (2-4 сөз)",
            "image_count": 1, // Неше сурет бар? Тек 1, 2 немесе 4 бола алады.
            "text_position": "bottom", // Мәтін қайда орналасқан? "top", "center", "bottom"
            "text_align": "left" // Мәтін қалай тураланған? "left", "center", "right"
        }
        МАҢЫЗДЫ: Тек қана дұрыс JSON қайтар, басқа ештеңе жазба.
        """
        payload = {
            "model": "qwen3",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                    ]
                }
            ],
            "temperature": 0.1
        }
        try:
            res = requests.post(self.gpt_url, headers=self.gpt_headers, json=payload).json()
            content = res['choices'][0]['message']['content'].strip()
            start, end = content.find('{'), content.rfind('}') + 1
            return json.loads(content[start:end])
        except Exception as e:
            print(f"❌ Vision Code Error: {e}")
            return None

    def evaluate_content(self, plan):
        print("⚖️ [Critic] Контент бағалануда...")
        prompt = f"Сен - қатал AI-Критиксің. Мына контентті бағала:\nТақырып: {plan.get('title', '')}\nМәтін: {plan.get('caption', '')}\n\nВиралдылық бағасы: [1-10]/10\n✅ Мықты тұсы: [1 сөйлем]\n⚠️ Тәуекел: [1 сөйлем]"
        payload = {"model": "qwen3", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
        try:
            return requests.post(self.gpt_url, headers=self.gpt_headers, json=payload).json()['choices'][0]['message']['content'].strip()
        except: return "Бағалау жүйесі уақытша қолжетімсіз."

    def generate_content_plan(self, topic, format_type, layout_data=None):
        print(f"🧠 [LLM] {format_type} жоспары жасалуда: {topic}")
        
        # Если есть шаблон, генерируем точное количество промптов
        img_count = layout_data.get("image_count", 4) if layout_data else (4 if format_type == "single" else 1)
        prompts_array = ", ".join([f'"Detailed english prompt for {topic}, NO TEXT"' for _ in range(img_count)])

        if format_type == "single" or layout_data:
            prompt = f"""
            Сен - элитный AI-маркетолог. Тема: {topic}. 
            Барлық мәтін ҚАЗАҚ ТІЛІНДЕ.
            Верни ТОЛЬКО JSON:
            {{
                "title": "ҚЫСҚА КҮШТІ ТАҚЫРЫП (2-4 сөз)",
                "subtitle": "Түсіндірме мәтін (8-12 сөз)",
                "caption": "Инстаграмға арналған пост мәтіні",
                "prompts": [{prompts_array}]
            }}
            """
        elif format_type == "carousel":
            prompt = f"""
            Сен - элитный AI-маркетолог. Тема: {topic}. Формат: КАРУСЕЛЬ.
            Верни ТОЛЬКО JSON:
            {{
                "title": "БАСТЫ ТАҚЫРЫП",
                "subtitle": "Мұқабаға арналған мәтін",
                "caption": "Инстаграмға арналған пост мәтіні",
                "slides": [
                    {{"prompt": "Detailed english visual prompt, NO TEXT", "text": ""}},
                    {{"prompt": "Another english prompt, NO TEXT", "text": "2-ші беттегі қысқаша мәтін"}},
                    {{"prompt": "Final english prompt, NO TEXT", "text": "3-ші беттегі қорытынды мәтін"}}
                ]
            }}
            """
        else:
            prompt = f"Сен - элитный AI-маркетолог. Тема: {topic}. Формат: STORY. Верни ТОЛЬКО JSON: {{\"text\": \"Қысқа мәтін\", \"prompt\": \"Detailed visual prompt, vertical\"}}"
        
        payload = {"model": "qwen3", "messages": [{"role": "user", "content": prompt}], "temperature": 0.5}
        try:
            res = requests.post(self.gpt_url, headers=self.gpt_headers, json=payload).json()
            content = res['choices'][0]['message']['content']
            return json.loads(content[content.find('{'):content.rfind('}') + 1])
        except Exception as e: return None

    def generate_image(self, prompt, is_story=False):
        print(f"🎨 [QWEN] Сурет генерациялануда...")
        clean_prompt = f"{prompt}. High-end editorial photography, cinematic lighting, 8k resolution, ultra-detailed. ABSOLUTELY NO TEXT, NO LETTERS, NO WATERMARKS."
        payload = {"model": "text-to-image", "prompt": clean_prompt, "n": 1, "size": "1024x1024"}
        try:
            res = requests.post(self.img_url, headers=self.img_headers, json=payload).json()
            item = res['data'][0]
            if item.get('b64_json'): img = Image.open(io.BytesIO(base64.b64decode(item['b64_json']))).convert("RGBA")
            elif item.get('url'): img = Image.open(io.BytesIO(requests.get(item['url']).content)).convert("RGBA")
            
            if is_story:
                width, height = img.size
                new_width = int(height * (9/16))
                left = (width - new_width) / 2
                img = img.crop((left, 0, left + new_width, height))
            return img
        except Exception as e: return None
