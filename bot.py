import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
ADMIN_BOT_TOKEN = "8613361813:AAEVdEsqUJzDDTwYX-Qe7Bqk88LFHAbPuqQ"
USER_BOT_TOKEN = "8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk"
CHANNEL_ID = -1003534114738
ALLOWED_ADMINS = [7952300659, 8592008935]

# Инициализация
admin_bot = Bot(token=ADMIN_BOT_TOKEN, default_parse_mode=ParseMode.HTML)
user_bot = Bot(token=USER_BOT_TOKEN, default_parse_mode=ParseMode.HTML)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- WEB SERVER ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="БОТ РАБОТАЕТ")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ЛОГИКА ПРИЕМЩИКА ---

@dp.message(F.video | F.animation | F.document)
async def handle_edit(message: types.Message, bot: Bot):
    if bot.token != USER_BOT_TOKEN:
        return

    # Избегаем двоеточий внутри f-строк
    uid = message.from_user.id
    uname = message.from_user.username
    
    if uname:
        creator = f"@{uname}"
    else:
        creator = f"ID {uid}"

    # Создаем кнопки (inline-клавиатура v3.x)
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ ПРИНЯТЬ", callback_data=f"ok_{uid}"))
    builder.row(types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"no_{uid}"))

    caption = f"<b>🎬 ЭДИТ\nСОЗДАТЕЛЬ ЭДИТА — {creator}\nПРИНЯТЬ ИЛИ ОТКЛОНИТЬ?</b>"

    for admin_id in ALLOWED_ADMINS:
        try:
            # Копируем сообщение админам
            await admin_bot.copy_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id,
                caption=caption,
                reply_markup=builder.as_markup()
            )
        except Exception as e:
            logging.error(f"Ошибка: {e}")

    await message.answer("<b>🚀 ТВОЙ ЭДИТ ОТПРАВЛЕН НА ПРОВЕРКУ!</b>")

# --- ЛОГИКА АДМИН-БОТА ---

@dp.callback_query(lambda c: c.data.startswith(("ok_", "no_")))
async def process_decision(callback: types.CallbackQuery, bot: Bot):
    if bot.token != ADMIN_BOT_TOKEN:
        return
        
    if callback.from_user.id not in ALLOWED_ADMINS:
        await callback.answer("НЕТ ДОСТУПА")
        return

    # Разделяем данные
    parts = callback.data.split("_")
    action = parts[0]
    user_id = int(parts[1])

    if action == "ok":
        # Жирный текст для канала
        chan_text = f"<b>🔥 НОВЫЙ ЭДИТ В КАНАЛЕ!\nАВТОР — ID {user_id}</b>"
        
        try:
            await admin_bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                caption=chan_text
            )
            await callback.message.edit_caption(caption="<b>✅ ОПУБЛИКОВАНО!</b>")
            await user_bot.send_message(user_id, "<b>🌟 ТВОЙ ЭДИТ ПРИНЯТ!</b>")
        except Exception as e:
            await callback.answer(f"ОШИБКА: {e}")

    elif action == "no":
        await callback.message.edit_caption(caption="<b>❌ ОТКЛОНЕНО.</b>")
        try:
            await user_bot.send_message(user_id, "<b>😔 ТВОЙ ЭДИТ ОТКЛОНЕН.</b>")
        except:
            pass
            
    await callback.answer()

# --- ЗАПУСК ---

async def main():
    # Запускаем сервер и ботов
    loop = asyncio.get_event_loop()
    loop.create_task(start_web_server())
    await dp.start_polling(user_bot, admin_bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("БОТ ОСТАНОВЛЕН")
        
