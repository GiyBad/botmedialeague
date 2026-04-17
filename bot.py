import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.enums import ParseMode

# --- НАСТРОЙКИ ---
ADMIN_BOT_TOKEN = "8613361813:AAEVdEsqUJzDDTwYX-Qe7Bqk88LFHAbPuqQ"
USER_BOT_TOKEN = "8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk"

CHANNEL_ID = -1003534114738
ALLOWED_ADMINS = [7952300659, 8592008935]

# Инициализация ботов с поддержкой HTML по умолчанию
admin_bot = Bot(token=ADMIN_BOT_TOKEN, default_parse_mode=ParseMode.HTML)
user_bot = Bot(token=USER_BOT_TOKEN, default_parse_mode=ParseMode.HTML)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- ЛОГИКА ПРИЕМЩИКА (USER_BOT) ---

@dp.message(F.video | F.animation | F.document)
async def handle_edit(message: types.Message, bot: Bot):
    if bot.token != USER_BOT_TOKEN:
        return

    # Формируем имя создателя
    username = f"@{message.from_user.username}" if message.from_user.username else f"ID: {message.from_user.id}"
    
    # Определяем тип медиа
    file_id = ""
    if message.video:
        file_id = message.video.file_id
    elif message.animation:
        file_id = message.animation.file_id
    elif message.document:
        file_id = message.document.file_id

    builder = InlineKeyboardBuilder()
    # Кнопки с данными для админов
    builder.button(text="✅ ПРИНЯТЬ", callback_data=f"ok_{message.from_user.id}")
    builder.button(text="❌ ОТКЛОНИТЬ", callback_data=f"no_{message.from_user.id}")
    builder.adjust(1)

    # Жирный текст для админа
    caption = f"<b>🎬 ЭДИТ\nСОЗДАТЕЛЬ ЭДИТА — {username}\nПРИНЯТЬ ИЛИ ОТКЛОНИТЬ?</b>"

    for admin_id in ALLOWED_ADMINS:
        try:
            if message.video:
                await admin_bot.send_video(admin_id, file_id, caption=caption, reply_markup=builder.as_markup())
            elif message.animation:
                await admin_bot.send_animation(admin_id, file_id, caption=caption, reply_markup=builder.as_markup())
            else:
                await admin_bot.send_document(admin_id, file_id, caption=caption, reply_markup=builder.as_markup())
        except Exception as e:
            logging.error(f"ОШИБКА ОТПРАВКИ АДМИНУ: {e}")

    await message.answer("<b>🚀 ТВОЙ ЭДИТ ОТПРАВЛЕН НА ПРОВЕРКУ!</b>")

# --- ЛОГИКА АДМИН-БОТА (ADMIN_BOT) ---

@dp.callback_query(F.data.startswith("ok_") | F.data.startswith("no_"))
async def process_decision(callback: types.CallbackQuery, bot: Bot):
    if bot.token != ADMIN_BOT_TOKEN or callback.from_user.id not in ALLOWED_ADMINS:
        return

    data = callback.data.split("_")
    action = data[0]
    user_id = int(data[1])

    if action == "ok":
        # Извлекаем данные из сообщения админа
        file_id = ""
        caption_in_channel = f"<b>🔥 НОВЫЙ ЭДИТ В КАНАЛЕ!\nАВТОР: <a href='tg://user?id={user_id}'>ССЫЛКА НА МАСТЕРА</a></b>"

        try:
            if callback.message.video:
                await admin_bot.send_video(CHANNEL_ID, callback.message.video.file_id, caption=caption_in_channel)
            elif callback.message.animation:
                await admin_bot.send_animation(CHANNEL_ID, callback.message.animation.file_id, caption=caption_in_channel)
            elif callback.message.document:
                await admin_bot.send_document(CHANNEL_ID, callback.message.document.file_id, caption=caption_in_channel)
            
            await callback.message.edit_caption(caption="<b>✅ ПРИНЯТО И ОПУБЛИКОВАНО!</b>")
            await user_bot.send_message(user_id, "<b>🌟 ТВОЙ ЭДИТ ПРИНЯТ И ОПУБЛИКОВАН В КАНАЛЕ!</b>")
        except Exception as e:
            await callback.answer(f"ОШИБКА: {e}", show_alert=True)

    elif action == "no":
        await callback.message.edit_caption(caption="<b>❌ ЭДИТ ОТКЛОНЕН.</b>")
        try:
            await user_bot.send_message(user_id, "<b>😔 ТВОЙ ЭДИТ БЫЛ ОТКЛОНЕН АДМИНИСТРАЦИЕЙ.</b>")
        except:
            pass

    await callback.answer()

async def main():
    # ЗАПУСК ОБОИХ БОТОВ
    await dp.start_polling(user_bot, admin_bot)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pr
        int("БОТ ВЫКЛЮЧЕН")
