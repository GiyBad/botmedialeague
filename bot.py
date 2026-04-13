import asyncio
import logging
from datetime import datetime, timedelta
import pytz

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
import uvicorn

# --- НАСТРОЙКИ ---
API_TOKEN = '8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk'
ADMIN_IDS = [7952300659, 6697881894] 
MAIN_CHANNEL = -1003534114738
TIMEZONE = pytz.timezone('Europe/Moscow')

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)
app = FastAPI()

@app.get("/")
async def root(): return {"status": "premium_bot_online"}

class PostState(StatesGroup):
    waiting_for_mode = State()
    waiting_for_second_post = State()
    waiting_for_date_type = State()
    waiting_for_custom_date = State()
    waiting_for_time = State()

async def send_forward(from_chat_id, message_ids):
    try:
        for m_id in message_ids:
            await bot.forward_message(chat_id=MAIN_CHANNEL, from_chat_id=from_chat_id, message_id=m_id)
            await asyncio.sleep(0.3)
        await bot.send_message(from_chat_id, "💎 **Успешно!**\nПост опубликован в канале.")
    except Exception as e:
        await bot.send_message(from_chat_id, f"⚠️ **Ошибка публикации:**\n{e}")

@dp.message(Command("start"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_start(m: types.Message, state: FSMContext):
    await state.clear()
    await m.answer(
        "👋 **Добро пожаловать в MediaLeague Planner!**\n\n"
        "Отправьте мне любое сообщение (текст, фото, видео), и я помогу запланировать его публикацию."
    )

@dp.message(F.from_user.id.in_(ADMIN_IDS))
async def handle_post(m: types.Message, state: FSMContext):
    if m.text == "/start": return
    curr = await state.get_state()
    
    if curr == PostState.waiting_for_second_post:
        data = await state.get_data()
        ids = data['msg_ids']
        ids.append(m.message_id)
        await state.update_data(msg_ids=ids)
        await ask_day(m, state)
        return
    
    if curr in [PostState.waiting_for_time, PostState.waiting_for_custom_date]: return

    await state.update_data(msg_ids=[m.message_id], chat_id=m.chat.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="📦 Одиночный", callback_data="mode_single")
    kb.button(text="👥 Дуплет (2 поста)", callback_data="mode_double")
    
    await m.answer(
        "📥 **Контент получен!**\nКак будем публиковать?",
        reply_markup=kb.as_markup()
    )
    await state.set_state(PostState.waiting_for_mode)

@dp.callback_query(F.data.startswith("mode_"))
async def set_mode(c: types.CallbackQuery, state: FSMContext):
    if c.data == "mode_single": 
        await ask_day(c.message, state)
    else:
        await c.message.edit_text("🔄 **Жду вторую часть...**\nПришлите следующее сообщение:")
        await state.set_state(PostState.waiting_for_second_post)
    await c.answer()

async def ask_day(m: types.Message, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="☀️ Сегодня", callback_data="day_today")
    kb.button(text="🌙 Завтра", callback_data="day_tomorrow")
    kb.button(text="📅 Календарь", callback_data="day_custom")
    kb.adjust(2, 1)
    
    text = "🗓 **Выберите день публикации:**"
    if isinstance(m, types.Message): await m.answer(text, reply_markup=kb.as_markup())
    else: await m.edit_text(text, reply_markup=kb.as_markup())
    await state.set_state(PostState.waiting_for_date_type)

@dp.callback_query(F.data.startswith("day_"))
async def set_day(c: types.CallbackQuery, state: FSMContext):
    now = datetime.now(TIMEZONE)
    if "today" in c.data: d = now.strftime("%d.%m")
    elif "tomorrow" in c.data: d = (now + timedelta(days=1)).strftime("%d.%m")
    else:
        await c.message.edit_text("⌨️ **Введите дату вручную**\nФормат: `ДД.ММ` (например, `15.04`)")
        await state.set_state(PostState.waiting_for_custom_date)
        return
    
    await state.update_data(date=d)
    await c.message.edit_text(f"🕒 **Дата установлена: {d}**\n\nВведите время (например, `15:30`):")
    await state.set_state(PostState.waiting_for_time)

@dp.message(PostState.waiting_for_custom_date)
async def custom_d(m: types.Message, s: FSMContext):
    await s.update_data(date=m.text.strip())
    await m.answer("🕒 **Принято!** Теперь введите время публикации (`ЧЧ:ММ`):")
    await s.set_state(PostState.waiting_for_time)

@dp.message(PostState.waiting_for_time)
async def set_t(m: types.Message, s: FSMContext):
    data = await s.get_data()
    try:
        now = datetime.now(TIMEZONE)
        target = datetime.strptime(f"{data['date']} {m.text.strip()}", "%d.%m %H:%M").replace(year=now.year)
        target = TIMEZONE.localize(target)
        if target < now: 
            return await m.answer("⏳ **Упс! Это время уже в прошлом.**\nПопробуйте еще раз:")
            
        scheduler.add_job(send_forward, 'date', run_date=target, args=[data['chat_id'], data['msg_ids']])
        
        await m.answer(
            f"✅ **Готово к отправке!**\n\n"
            f"📅 Дата: `{target.strftime('%d.%m.%Y')}`\n"
            f"⏰ Время: `{target.strftime('%H:%M')}` МСК\n\n"
            f"Я сообщу, когда пост выйдет."
        )
        await s.clear()
    except: 
        await m.answer("⚠️ **Неверный формат времени!**\nИспользуйте формат `ЧЧ:ММ` (например, `09:00`)")

async def main():
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    config = uvicorn.Config(app, host="0.0.0.0", port=8000, loop="asyncio")
    server = uvicorn.Server(config)
    await asyncio.gather(dp.start_polling(bot), server.serve())

if __name__ == '__main__':
    asyncio.run(main())
