import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ (Вставь свои токены) ---
ADMIN_BOT_TOKEN = "8613361813:AAEVdEsqUJzDDTwYX-Qe7Bqk88LFHAbPuqQ"
USER_BOT_TOKEN = "8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk"
CHANNEL_ID = -1003534114738
ALLOWED_ADMINS = [7952300659, 8592008935]

# Инициализация
admin_bot = Bot(token=ADMIN_BOT_TOKEN, default_parse_mode=ParseMode.HTML)
user_bot = Bot(token=USER_BOT_TOKEN, default_parse_mode=ParseMode.HTML)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- WEB SERVER ДЛЯ RENDER (Чтобы сервис не засыпал) ---
async def handle(request):
    return web.Response(text="БОТ ЖИВ 🚀")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    # Render дает порт в переменной окружения PORT
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ЛОГИКА ПРИЕМЩИКА ---

@dp.message(F.video | F.animation | F.document)
async def handle_edit(message: types.Message, bot: Bot):
    if bot.token != USER_BOT_TOKEN:
        return

    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    
    # Забираем file_id
    file_id = (message.video.file_id if message.video 
               else message.animation.file_id if message.animation 
               else message.document.file_id)

    builder = InlineKeyboardBuilder()
    builder.button(text="✅ ПРИНЯТЬ", callback_data=f"ok_{message.from_user.id}")
    builder.button(text="❌ ОТКЛОНИТЬ", callback_data=f"no_{message.from_user.id}")
    builder.adjust(1)

    caption = f"<b>🎬 ЭДИТ\nСОЗДАТЕЛЬ ЭДИТА — {username}\nПРИНЯТЬ ИЛИ ОТКЛОНИТЬ?</b>"

    for admin_id in ALLOWED_ADMINS:
        try:
            await admin_bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption,
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            logging.error(f"ОШИБКА ПЕРЕСЫЛКИ: {e}")

    await message.answer("<b>🚀 ТВОЙ ЭДИТ ОТПРАВЛЕН НА ПРОВЕРКУ!</b>")

# --- ЛОГИКА АДМИН-БОТА ---

@dp.callback_query(F.data.startswith("ok_") | F.data.startswith("no_"))
async def process_decision(callback: types.CallbackQuery, bot: Bot):
    if bot.token != ADMIN_BOT_TOKEN or callback.from_user.id not in ALLOWED_ADMINS:
        return

    action, user_id = callback.data.split("_")

    if action == "ok":
        caption_chan = f"<b>🔥 НОВЫЙ ЭДИТ В КАНАЛЕ!\nАВТОР — <a href='tg://user?id={user_id}'>МАСТЕР</a></b>"
        
        try:
            # Публикуем в канал через копирование (самый надежный метод)
            await admin_bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                caption=caption_chan
            )
            await callback.message.edit_caption(caption="<b>✅ ОПУБЛИКОВАНО!</b>")
            await user_bot.send_message(user_id, "<b>🌟 ТВОЙ ЭДИТ ОПУБЛИКОВАН В КАНАЛЕ!</b>")
        except Exception as e:
            await callback.answer(f"ОШИБКА: {e}", show_alert=True)

    elif action == "no":
        await callback.message.edit_caption(caption="<b>❌ ОТКЛОНЕНО.</b>")
        try:
            await user_bot.send_message(user_id, "<b>😔 ТВОЙ ЭДИТ ОТКЛОНЕН.</b>")
        except:
            pass
    await callback.answer()

# --- ЗАПУСК ---

async def main():
    # Запускаем веб-сервер и ботов параллельно
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(user_bot, admin_bot)
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInte
    rrupt:
        pass
