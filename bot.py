import asyncio
import logging
import requests
import os
import base64
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton

from engine import AlemEngine
import renderer

load_dotenv()
logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
META_ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
INSTA_BUSINESS_ID = os.getenv("INSTA_BUSINESS_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
ai_engine = AlemEngine()
user_data_store = {}

class Flow(StatesGroup):
    waiting_for_format = State()
    waiting_for_topic = State()
    waiting_for_manual_topic = State()

def upload_to_catbox(image_path):
    try:
        with open(image_path, 'rb') as f:
            res = requests.post("https://catbox.moe/user/api.php", files={'reqtype': (None, 'fileupload'), 'fileToUpload': f})
            if res.status_code == 200: return res.text.strip()
    except Exception as e: return None

@dp.message(Command("start"))
async def start_cmd(message: types.Message, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 Бір беттік пост (Коллаж)", callback_data="fmt_single")],
        [InlineKeyboardButton(text="📚 Карусель (Бірнеше бет)", callback_data="fmt_carousel")],
        [InlineKeyboardButton(text="📱 Сторис (Vertical)", callback_data="fmt_story")]
    ])
    await message.answer("🚀 **Alem Content Bot v5.0 (AI-Cloner)**\n\nҚандай форматта контент жасаймыз?", reply_markup=kb)
    await state.set_state(Flow.waiting_for_format)

@dp.callback_query(F.data.startswith("fmt_"))
async def choose_format(callback: types.CallbackQuery, state: FSMContext):
    fmt = callback.data.split("_")[1]
    await state.update_data(format_type=fmt)
    await callback.message.edit_text(
        "Тамаша! Енді маған мыналардың **біреуін** жіберіңіз:\n"
        "1️⃣ Тақырыпты текстпен жазыңыз ✍️\n"
        "2️⃣ Дауыстық хабарлама жіберіңіз (STT) 🎙\n"
        "3️⃣ Дайын шаблон немесе сурет жіберіңіз (Vision) 🖼️"
    )
    await state.set_state(Flow.waiting_for_topic)

@dp.message(Flow.waiting_for_topic, F.voice)
async def handle_voice(message: types.Message, state: FSMContext):
    status = await message.answer("🎙 Аудио талдануда...")
    file_id = message.voice.file_id
    file = await bot.get_file(file_id)
    file_path = f"voice_{message.from_user.id}.ogg"
    await bot.download_file(file.file_path, file_path)
    text = ai_engine.transcribe_audio(file_path)
    os.remove(file_path)
    if not text: return await status.edit_text("❌ Аудионы тану мүмкін болмады.")
    await status.edit_text(f"Тамаша! Тақырып: **{text}**")
    await execute_pipeline(message.chat.id, message.from_user.id, text, state, status)

# --- НОВАЯ ЛОГИКА: AI ШПИОН ИЗВЛЕКАЕТ СТРУКТУРУ ---
@dp.message(Flow.waiting_for_topic, F.photo)
async def handle_photo(message: types.Message, state: FSMContext):
    status = await message.answer("👁️ Шаблон талдануда (Vision)...")
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = f"photo_{message.from_user.id}.jpg"
    await bot.download_file(file.file_path, file_path)

    with open(file_path, "rb") as f: b64_image = base64.b64encode(f.read()).decode('utf-8')
    os.remove(file_path)

    # Получаем JSON структуру
    layout_data = ai_engine.analyze_competitor_image(b64_image)
    if not layout_data: return await status.edit_text("❌ Шаблонды талдау мүмкін болмады.")

    topic = layout_data.get("suggested_topic", "Бизнес")
    await state.update_data(layout=layout_data) # Сохраняем схему дизайна

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🤖 Иә, '{topic}' тақырыбы", callback_data=f"topic_auto_{topic}")],
        [InlineKeyboardButton(text="✍️ Жоқ, өзім жазамын", callback_data="topic_manual")]
    ])
    await status.delete()
    await message.answer(f"🖼 **Шаблон құрылымы көшірілді!**\n\nСурет саны: {layout_data.get('image_count')}\nМәтін орны: {layout_data.get('text_position')}\n\nAI ұсынған тақырып: **{topic}**\nОсыны қолданамыз ба?", reply_markup=kb)

@dp.callback_query(F.data.startswith("topic_auto_"))
async def process_topic_auto(callback: types.CallbackQuery, state: FSMContext):
    topic = callback.data.replace("topic_auto_", "")
    status = await callback.message.edit_text("⏳ **Авто-генерация басталды...**")
    await execute_pipeline(callback.message.chat.id, callback.from_user.id, topic, state, status)

@dp.callback_query(F.data == "topic_manual")
async def process_topic_manual(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("✍️ Осы шаблонға арналған тақырыпты мәтінмен немесе дауыстық хабарламамен жіберіңіз:")
    await state.set_state(Flow.waiting_for_manual_topic)

@dp.message(Flow.waiting_for_manual_topic, F.text)
async def manual_topic_text(message: types.Message, state: FSMContext):
    status = await message.answer("⏳ **AI жоспар құруда...**")
    await execute_pipeline(message.chat.id, message.from_user.id, message.text, state, status)

@dp.message(Flow.waiting_for_topic, F.text)
async def handle_text(message: types.Message, state: FSMContext):
    status = await message.answer("⏳ **AI жоспар құруда...**")
    await execute_pipeline(message.chat.id, message.from_user.id, message.text, state, status)

# --- ГЛАВНЫЙ ПАЙПЛАЙН С УЧЕТОМ LAYOUT ---
async def execute_pipeline(chat_id, user_id, topic, state, status_msg):
    data = await state.get_data()
    fmt = data.get("format_type")
    layout_data = data.get("layout", None) # Берем схему дизайна, если есть
    
    plan = ai_engine.generate_content_plan(topic, fmt, layout_data)
    if not plan: return await status_msg.edit_text("❌ Қате: LLM жауап бермеді.")

    await status_msg.edit_text("🎨 **Суреттер генерациялануда...**")
    
    if fmt == "single" or layout_data:
        images = [ai_engine.generate_image(p) for p in plan['prompts']]
        images = [i for i in images if i]
        # Используем ДИНАМИЧЕСКИЙ рендерер, прокидывая схему от ИИ
        final_path = renderer.create_dynamic_clone(images, plan['title'], plan['subtitle'], layout_data)
        media_paths = [final_path]
    elif fmt == "carousel":
        images = [ai_engine.generate_image(s['prompt']) for s in plan['slides']]
        media_paths = renderer.create_carousel_pages([i for i in images if i], plan['slides'], plan['title'], plan['subtitle'])
    else:
        img = ai_engine.generate_image(plan['prompt'], is_story=True)
        final_path = renderer.create_story(img, plan['text'])
        media_paths = [final_path]

    await status_msg.edit_text("⚖️ **AI-Критик контентті бағалауда...**")
    critique = ai_engine.evaluate_content(plan)
    final_caption = f"{plan.get('caption', '')}\n\n---\n🤖 **AI-КРИТИК БАҒАСЫ:**\n{critique}"
    user_data_store[user_id] = {"format": fmt, "paths": media_paths, "caption": final_caption}

    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🚀 Instagram-ға ЖАРИЯЛАУ", callback_data="publish_insta")]])
    await status_msg.delete()
    if fmt == "carousel" and not layout_data:
        media_group = [types.InputMediaPhoto(media=FSInputFile(p), caption=final_caption if i==0 else "") for i, p in enumerate(media_paths)]
        await bot.send_media_group(chat_id, media=media_group)
        await bot.send_message(chat_id, "Жариялауға дайынсыз ба?", reply_markup=kb)
    else:
        await bot.send_photo(chat_id, photo=FSInputFile(media_paths[0]), caption=final_caption, reply_markup=kb)
    await state.clear()

@dp.callback_query(F.data == "publish_insta")
async def publish(callback: types.CallbackQuery):
    data = user_data_store.get(callback.from_user.id)
    if not data: return await callback.answer("Мәлімет жоқ.")
    progress = await callback.message.answer("📡 Meta API-ге жіберілуде...")
    try:
        if data["format"] == "single" or len(data["paths"]) == 1:
            url = upload_to_catbox(data["paths"][0])
            res = requests.post(f"https://graph.facebook.com/v19.0/{INSTA_BUSINESS_ID}/media", data={'image_url': url, 'caption': data['caption'], 'access_token': META_ACCESS_TOKEN}).json()
            requests.post(f"https://graph.facebook.com/v19.0/{INSTA_BUSINESS_ID}/media_publish", data={'creation_id': res['id'], 'access_token': META_ACCESS_TOKEN})
        else:
            await progress.edit_text("📡 Карусель суреттері жүктелуде...")
            container_ids = []
            for path in data["paths"]:
                url = upload_to_catbox(path)
                res = requests.post(f"https://graph.facebook.com/v19.0/{INSTA_BUSINESS_ID}/media", data={'image_url': url, 'is_carousel_item': 'true', 'access_token': META_ACCESS_TOKEN}).json()
                container_ids.append(res['id'])
            res_car = requests.post(f"https://graph.facebook.com/v19.0/{INSTA_BUSINESS_ID}/media", data={'media_type': 'CAROUSEL', 'children': ','.join(container_ids), 'caption': data['caption'], 'access_token': META_ACCESS_TOKEN}).json()
            await asyncio.sleep(15) 
            requests.post(f"https://graph.facebook.com/v19.0/{INSTA_BUSINESS_ID}/media_publish", data={'creation_id': res_car['id'], 'access_token': META_ACCESS_TOKEN})
        await progress.edit_text("✅ **СӘТТІ ЖАРИЯЛАНДЫ!** 🎉")
    except Exception as e: await progress.edit_text(f"❌ Қате: {e}")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("🚀 Alem Content Bot v5.0 is running...")
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
