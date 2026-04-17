import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
# Убедись, что токены не перепутаны! 
# ПЕРВЫЙ (Admin) - тот что принимает решения. ВТОРОЙ (User) - тот куда шлют видео.
ADMIN_BOT_TOKEN = "8613361813:AAEVdEsqUJzDDTwYX-Qe7Bqk88LFHAbPuqQ"
USER_BOT_TOKEN = "8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk"

CHANNEL_ID = -1003534114738
ALLOWED_ADMINS = [7952300659, 8592008935]

# Инициализация (ParseMode указываем сразу здесь)
admin_bot = Bot(token=ADMIN_BOT_TOKEN, parse_mode=ParseMode.HTML)
user_bot = Bot(token=USER_BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- ВЕБ-СЕРВЕР (Для Render) ---
async def handle(request):
    return web.Response(text="БОТ РАБОТАЕТ")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    await web.TCPSite(runner, "0.0.0.0", port).start()

# --- ЛОГИКА ---

@dp.message(F.video | F.animation | F.document)
async def handle_edit(message: types.Message, bot: Bot):
    # Если сообщение пришло НЕ в тот бот, который принимает эдиты — игнорим
    if bot.token != USER_BOT_TOKEN:
        return

    uid = message.from_user.id
    creator = f"@{message.from_user.username}" if message.from_user.username else f"ID {uid}"

    # Клавиатура
    from aiogram.utils.keyboard import InlineKeyboardBuilder
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="✅ ПРИНЯТЬ", callback_data=f"ok_{uid}"))
    builder.row(types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"no_{uid}"))

    caption = f"<b>🎬 ЭДИТ\nСОЗДАТЕЛЬ — {creator}\nПРИНЯТЬ ИЛИ ОТКЛОНИТЬ?</b>"

    for admin_id in ALLOWED_ADMINS:
        try:
            # Используем прямой метод отправки видео через Админ-бота
            if message.video:
                await admin_bot.send_video(admin_id, message.video.file_id, caption=caption, reply_markup=builder.as_markup())
            elif message.animation:
                await admin_bot.send_animation(admin_id, message.animation.file_id, caption=caption, reply_markup=builder.as_markup())
            else:
                await admin_bot.send_document(admin_id, message.document.file_id, caption=caption, reply_markup=builder.as_markup())
        except Exception as e:
            logging.error(f"Ошибка отправки админу {admin_id}: {e}")

    await message.answer("<b>🚀 ТВОЙ ЭДИТ ОТПРАВЛЕН НА ПРОВЕРКУ!</b>")

@dp.callback_query(F.data.startswith("ok_") | F.data.startswith("no_"))
async def process_decision(callback: types.CallbackQuery, bot: Bot):
    # Только админ-бот должен реагировать на кнопки
    if bot.token != ADMIN_BOT_TOKEN:
        return

    action, user_id = callback.data.split("_")

    if action == "ok":
        try:
            # Пересылаем в канал
            await admin_bot.copy_message(chat_id=CHANNEL_ID, from_chat_id=callback.message.chat.id, message_id=callback.message.message_id, caption=f"<b>🔥 НОВЫЙ ЭДИТ!\nАВТОР: ID {user_id}</b>")
            await callback.message.edit_caption(caption="<b>✅ ОПУБЛИКОВАНО!</b>")
            await user_bot.send_message(user_id, "<b>🌟 ТВОЙ ЭДИТ ПРИНЯТ!</b>")
        except Exception as e:
            await callback.answer(f"ОШИБКА: {e}")
    else:
        await callback.message.edit_caption(caption="<b>❌ ОТКЛОНЕНО.</b>")
        await user_bot.send_message(user_id, "<b>😔 ОТКЛОНЕНО.</b>")
    
    await callback.answer()

async def main():
    # Запускаем всё вместе
    await asyncio.gather(
        start_web_server(),
        dp.start_polling(admin_bot, user_bot)
    )

if __name__ == "__main__":
    as
    yncio.run(main())
