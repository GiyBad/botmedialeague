import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
ADMIN_BOT_TOKEN = "8613361813:AAEVdEsqUJzDDTwYX-Qe7Bqk88LFHAbPuqQ"
USER_BOT_TOKEN = "8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk"

CHANNEL_ID = -1003534114738
ALLOWED_ADMINS = [7952300659, 8592008935]

# Инициализация ботов
admin_bot = Bot(token=ADMIN_BOT_TOKEN)
user_bot = Bot(token=USER_BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- ЛОГИКА ПРИЕМЩИКА (USER_BOT) ---

@dp.message(F.video | F.document | F.animation)
async def handle_edit(message: types.Message):
    """Принимает эдит от пользователя и пересылает админам через админ-бота"""
    username = f"@{message.from_user.username}" if message.from_user.username else "Без юзернейма"
    
    # Создаем кнопки для админ-бота
    builder = InlineKeyboardBuilder()
    # Кодируем callback данные: действие|id_пользователя|file_id|тип_файла
    file_id = message.video.file_id if message.video else (message.animation.file_id if message.animation else message.document.file_id)
    file_type = "video" if message.video else ("animation" if message.animation else "doc")
    
    builder.button(text="✅ Принять", callback_data=f"app_{message.from_user.id}_{file_id}_{file_type}")
    builder.button(text="❌ Отклонить", callback_data=f"rej_{message.from_user.id}")

    caption = f"🎬 **Новый Эдит!**\nСоздатель: {username}"

    # Отправляем каждому админу в админ-бот
    for admin_id in ALLOWED_ADMINS:
        try:
            if message.video:
                await admin_bot.send_video(admin_id, message.video.file_id, caption=caption, reply_markup=builder.as_markup())
            elif message.animation:
                await admin_bot.send_animation(admin_id, message.animation.file_id, caption=caption, reply_markup=builder.as_markup())
            else:
                await admin_bot.send_document(admin_id, message.document.file_id, caption=caption, reply_markup=builder.as_markup())
        except Exception as e:
            print(f"Ошибка отправки админу {admin_id}: {e}")

    await message.answer("🚀 Твой эдит отправлен на проверку!")

# --- ЛОГИКА АДМИН-БОТА (ADMIN_BOT) ---

@dp.callback_query(lambda c: c.data.startswith(('app_', 'rej_')))
async def process_decision(callback: types.CallbackQuery):
    """Обработка кнопок Принять/Отклонить в админ-боте"""
    
    # Проверка прав (только указанные ID)
    if callback.from_user.id not in ALLOWED_ADMINS:
        await callback.answer("У тебя нет прав!", show_alert=True)
        return

    data = callback.data.split('_')
    action = data[0]
    user_id = int(data[1])

    if action == "app":
        file_id = data[2]
        file_type = data[3]
        
        # Пересылаем в канал через админ-бота
        try:
            caption = f"🔥 Новый эдит в канале!\nОт: [id{user_id}](tg://user?id={user_id})"
            if file_type == "video":
                await admin_bot.send_video(CHANNEL_ID, file_id, caption=caption, parse_mode="Markdown")
            elif file_type == "animation":
                await admin_bot.send_animation(CHANNEL_ID, file_id, caption=caption, parse_mode="Markdown")
            else:
                await admin_bot.send_document(CHANNEL_ID, file_id, caption=caption, parse_mode="Markdown")
            
            await callback.message.edit_caption(caption="✅ **Опубликовано в канал!**")
            # Уведомляем автора
            await user_bot.send_message(user_id, "🌟 Твой эдит был опубликован в канале!")
        except Exception as e:
            await callback.answer(f"Ошибка: {e}", show_alert=True)

    elif action == "rej":
        await callback.message.edit_caption(caption="❌ **Эдит отклонен.**")
        try:
            await user_bot.send_message(user_id, "😔 К сожалению, твой эдит отклонен.")
        except:
            pass

    await callback.answer()

async def main():
    # Запускаем обоих ботов одновременно
    # Важно: aiogram 3.x поддерживает polling для нескольких ботов через один диспетчер
    await dp.start_polling(user_bot, admin_bot)

if __name__ == "__main__":
    as
    yncio.run(main())
