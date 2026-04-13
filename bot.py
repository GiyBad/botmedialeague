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

# --- НАСТРОЙКИ ---
API_TOKEN = '8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk'
ADMIN_IDS = [7952300659, 6697881894] 
MAIN_CHANNEL = -1003534114738
TIMEZONE = pytz.timezone('Europe/Moscow')

# Настройка логирования
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

# Для работы на Render (FastAPI заглушка)
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "bot is alive"}

# Состояния
class PostState(StatesGroup):
    waiting_for_mode = State()
    waiting_for_second_post = State()
    waiting_for_date_type = State()
    waiting_for_custom_date = State()
    waiting_for_time = State()

# Функция отправки
async def send_forward(from_chat_id, message_ids):
    try:
        for m_id in message_ids:
            await bot.forward_message(chat_id=MAIN_CHANNEL, from_chat_id=from_chat_id, message_id=m_id)
            await asyncio.sleep(0.3)
        await bot.send_message(from_chat_id, "✅ Пост(ы) опубликованы в канале!")
    except Exception as e:
        await bot.send_message(from_chat_id, f"❌ Ошибка: {e}")

@dp.message(Command("start"), F.from_user.id.in_(ADMIN_IDS))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🕹 **Бот готов!**\nПришли первый (или единственный) пост.")

@dp.message(F.from_user.id.in_(ADMIN_IDS))
async def handle_first_post(message: types.Message, state: FSMContext):
    if message.text == "/start": return
    
    curr = await state.get_state()
    if curr == PostState.waiting_for_second_post:
        data = await state.get_data()
        msg_list = data['msg_ids']
        msg_list.append(message.message_id)
        await state.update_data(msg_ids=msg_list)
        await ask_day(message, state)
        return
    
    if curr in [PostState.waiting_for_time, PostState.waiting_for_custom_date]:
        return

    await state.update_data(msg_ids=[message.message_id], chat_id=message.chat.id)
    kb = InlineKeyboardBuilder()
    kb.button(text="Один пост", callback_data="mode_single")
    kb.button(text="Добавить второй", callback_data="mode_double")
    await message.answer("📥 Принято. Это один пост или будет второй?", reply_markup=kb.as_markup())
    await state.set_state(PostState.waiting_for_mode)

@dp.callback_query(F.data.startswith("mode_"))
async def set_mode(call: types.CallbackQuery, state: FSMContext):
    if call.data == "mode_single":
        await ask_day(call.message, state)
    else:
        await call.message.edit_text("🆗 Пришли **второй** пост:")
        await state.set_state(PostState.waiting_for_second_post)
    await call.answer()

async def ask_day(m: types.Message, state: FSMContext):
    kb = InlineKeyboardBuilder()
    kb.button(text="Сегодня", callback_data="day_today")
    kb.button(text="Завтра", callback_data="day_tomorrow")
    kb.button(text="Дата", callback_data="day_custom")
    kb.adjust(2, 1)
    text = "📥 Когда публикуем?"
    if isinstance(m, types.Message): await m.answer(text, reply_markup=kb.as_markup())
    else: await m.edit_text(text, reply_markup=kb.as_markup())
    await state.set_state(PostState.waiting_for_date_type)

@dp.callback_query(F.data.startswith("day_"))
async def set_day(call: types.CallbackQuery, state: FSMContext):
    now = datetime.now(TIMEZONE)
    if "today" in call.data: d = now.strftime("%d.%m")
    elif "tomorrow" in call.data: d = (now + timedelta(days=1)).strftime("%d.%m")
    else:
        await call.message.edit_text("📅 Напиши дату (ДД.ММ):")
        await state.set_state(PostState.waiting_for_custom_date)
        return
    await state.update_data(date=d)
    await call.message.edit_text(f"📅 Дата: {d}. Напиши время (ЧЧ:ММ):")
    await state.set_state(PostState.waiting_for_time)

@dp.message(PostState.waiting_for_custom_date)
async def set_custom_date(m: types.Message, s: FSMContext):
    await s.update_data(date=m.text.strip())
    await m.answer("✅ Время (ЧЧ:ММ):")
    await s.set_state(PostState.waiting_for_time)

@dp.message(PostState.waiting_for_time)
async def set_time(m: types.Message, s: FSMContext):
    data = await s.get_data()
    try:
        now = datetime.now(TIMEZONE)
        target = datetime.strptime(f"{data['date']} {m.text.strip()}", "%d.%m %H:%M").replace(year=now.year)
        target = TIMEZONE.localize(target)
        if target < now: return await m.answer("❌ Время уже в прошлом!")
        
        scheduler.add_job(send_forward, 'date', run_date=target, args=[data['chat_id'], data['msg_ids']])
        await m.answer(f"🚀 Запланировано на {target.strftime('%d.%m %H:%M')}")
        await s.clear()
    except: await m.answer("⚠️ Ошибка формата! Например 15:30")

# Запуск бота и FastAPI
async def run_bot():
    scheduler.start()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    # Для локального запуска раскомментируй: 
    # asyncio.run(run_bot())
    
    # Для Render (через uvicorn в shell-скрипте) будет использоваться запуск uvicorn отдельно
    import uvicorn
    import threading

    def start_bot_thread():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_bot())

    threading.Thread(target=start_bot_thread, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)
                               
