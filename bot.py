import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
ADMIN_BOT_TOKEN = "8613361813:AAEVdEsqUJzDDTwYX-Qe7Bqk88LFHAbPuqQ"
USER_BOT_TOKEN = "8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk"
CHANNEL_ID = -1003534114738
ALLOWED_ADMINS = [7952300659, 8592008935]

# Инициализация ботов
admin_bot = Bot(token=ADMIN_BOT_TOKEN, parse_mode=ParseMode.HTML)
user_bot = Bot(token=USER_BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- WEB SERVER ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="BOT IS ALIVE")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ЛОГИКА ПРИЕМЩИКА (USER_BOT) ---
@dp.message(F.video | F.animation | F.document)
async def handle_edit(message: types.Message, bot: Bot):
    if bot.token != USER_BOT_TOKEN:
        return

    uid = message.from_user.id
    username = message.from_user.username
    creator = f"@{username}" if username else f"ID {uid}"

    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ ПРИНЯТЬ", callback_data=f"ok_{uid}"))
    builder.row(types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"no_{uid}"))

    text = f"<b>🎬 ЭДИТ\nСОЗДАТЕЛЬ ЭДИТА — {creator}\nПРИНЯТЬ ИЛИ ОТКЛОНИТЬ?</b>"

    for admin_id in ALLOWED_ADMINS:
        try:
            if message.video:
                await admin_bot.send_video(admin_id, message.video.file_id, caption=text, reply_markup=builder.as_markup())
            elif message.animation:
                await admin_bot.send_animation(admin_id, message.animation.file_id, caption=text, reply_markup=builder.as_markup())
            else:
                await admin_bot.send_document(admin_id, message.document.file_id, caption=text, reply_markup=builder.as_markup())
        except Exception as e:
            logging.error(f"Ошибка отправки админу {admin_id}: {e}")

    await message.answer("<b>🚀 ТВОЙ ЭДИТ ОТПРАВЛЕН НА ПРОВЕРКУ!</b>")

# --- ЛОГИКА АДМИН-БОТА ---
@dp.callback_query(F.data.startswith("ok_") | F.data.startswith("no_"))
async def process_decision(callback: types.CallbackQuery, bot: Bot):
    if bot.token != ADMIN_BOT_TOKEN:
        return

    if callback.from_user.id not in ALLOWED_ADMINS:
        return

    action, user_id = callback.data.split("_")

    if action == "ok":
        try:
            # Публикация в канал
            await admin_bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                caption=f"<b>🔥 НОВЫЙ ЭДИТ В КАНАЛЕ!\nАВТОР: <a href='tg://user?id={user_id}'>МАСТЕР</a></b>"
            )
            await callback.message.edit_caption(caption="<b>✅ ОПУБЛИКОВАНО!</b>")
            await user_bot.send_message(user_id, "<b>🌟 ТВОЙ ЭДИТ ПРИНЯТ И ОПУБЛИКОВАН!</b>")
        except Exception as e:
            await callback.answer(f"ОШИБКА: {e}", show_alert=True)
    else:
        await callback.message.edit_caption(caption="<b>❌ ОТКЛОНЕНО.</b>")
        try:
            await user_bot.send_message(user_id, "<b>😔 ТВОЙ ЭДИТ ОТКЛОНЕН.</b>")
        except:
            pass
    
    await callback.answer()

# --- ПРАВИЛЬНЫЙ ЗАПУСК БЕЗ ОШИБОК СИНТАКСИСА ---
async def main():
    # Запускаем веб-сервер фоновой задачей
    asyncio.create_task(start_web_server())
    # Запускаем поллинг обоих ботов
    await dp.start_polling(admin_bot, user_bot)

if __name__ == "__main__":
    asy
                                           ncio.run(main())
