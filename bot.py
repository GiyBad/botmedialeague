import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
ADMIN_TOKEN = "8613361813:AAEVdEsqUJzDDTwYX-Qe7Bqk88LFHAbPuqQ"
USER_TOKEN = "8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk"
CHANNEL_ID = -1003534114738
ADMIN_IDS = [7952300659, 8592008935]

# Инициализация ботов
admin_bot = Bot(token=ADMIN_TOKEN, parse_mode=ParseMode.HTML)
user_bot = Bot(token=USER_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- ВЕБ-СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="БОТ ЖИВ")

async def run_server():
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
    if bot.token != USER_TOKEN:
        return

    uid = message.from_user.id
    name = message.from_user.username
    creator = f"@{name}" if name else f"ID {uid}"

    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ ПРИНЯТЬ", callback_data=f"ok_{uid}"))
    kb.row(types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"no_{uid}"))

    text = f"<b>🎬 ЭДИТ\nСОЗДАТЕЛЬ ЭДИТА — {creator}\nПРИНЯТЬ ИЛИ ОТКЛОНИТЬ?</b>"

    for admin_id in ADMIN_IDS:
        try:
            if message.video:
                await admin_bot.send_video(admin_id, message.video.file_id, caption=text, reply_markup=kb.as_markup())
            elif message.animation:
                await admin_bot.send_animation(admin_id, message.animation.file_id, caption=text, reply_markup=kb.as_markup())
            else:
                await admin_bot.send_document(admin_id, message.document.file_id, caption=text, reply_markup=kb.as_markup())
        except Exception as e:
            logging.error(f"Error: {e}")

    await message.answer("<b>🚀 ТВОЙ ЭДИТ ОТПРАВЛЕН НА ПРОВЕРКУ!</b>")

# --- ЛОГИКА АДМИН-БОТА ---
@dp.callback_query(F.data.startswith("ok_") | F.data.startswith("no_"))
async def process_decision(callback: types.CallbackQuery, bot: Bot):
    if bot.token != ADMIN_TOKEN or callback.from_user.id not in ADMIN_IDS:
        return

    action, user_id = callback.data.split("_")

    if action == "ok":
        try:
            await admin_bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                caption=f"<b>🔥 НОВЫЙ ЭДИТ!\nАВТОР: <a href='tg://user?id={user_id}'>МАСТЕР</a></b>"
            )
            await callback.message.edit_caption(caption="<b>✅ ОПУБЛИКОВАНО!</b>")
            await user_bot.send_message(user_id, "<b>🌟 ТВОЙ ЭДИТ ПРИНЯТ!</b>")
        except Exception as e:
            await callback.answer(f"ОШИБКА: {e}")
    else:
        await callback.message.edit_caption(caption="<b>❌ ОТКЛОНЕНО.</b>")
        await user_bot.send_message(user_id, "<b>😔 ОТКЛОНЕНО.</b>")
    
    await callback.answer()

# --- ЗАПУСК ---
async def main():
    # Запускаем сервер в фоне
    asyncio.ensure_future(run_server())
    # Запускаем ботов
    await dp.start_polling(admin_bot, user_bot, skip_updates=True)

if __name__ == "__main__":
    asyn
    cio.run(main())
