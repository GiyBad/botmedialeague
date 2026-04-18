import logging
import asyncio
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- НАСТРОЙКИ ---
ADMIN_TOKEN = "8613361813:AAEVdEsqUJzDDTwYX-Qe7Bqk88LFHAbPuqQ"
USER_TOKEN = "8319949264:AAEGh3TDOkA6ywtyFLTk2T3ggxF69BBsipk"
CHANNEL_ID = -1003534114738
ADMIN_IDS = [7952300659, 8592008935]

# Инициализация ботов
admin_bot = Bot(
    token=ADMIN_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
user_bot = Bot(
    token=USER_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

admin_dp = Dispatcher()
user_dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

# --- СЕРВЕР ДЛЯ RENDER ---
async def handle(request):
    return web.Response(text="BOTS ARE ALIVE")

async def run_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    logging.info(f"Сервер запущен на порту {port}")

# --- УВЕДОМЛЕНИЕ О ЗАПУСКЕ ---
async def notify_admins_on_start():
    for admin_id in ADMIN_IDS:
        try:
            await admin_bot.send_message(
                admin_id,
                "<b>🟢 БОТ ЗАПУЩЕН И ГОТОВ К РАБОТЕ!\n"
                "Жду новые эдиты от пользователей...</b>"
            )
            logging.info(f"Уведомление о запуске отправлено админу {admin_id}")
        except Exception as e:
            logging.error(f"Ошибка уведомления админа {admin_id}: {e}")

# --- АДМИН БОТ: КОМАНДЫ ---
@admin_dp.message(Command("start"))
async def admin_cmd_start(message: types.Message):
    logging.info(f"Админ-бот: /start от {message.from_user.id}")
    if message.from_user.id in ADMIN_IDS:
        await message.answer("<b>✅ АДМИН-ПАНЕЛЬ ВКЛЮЧЕНА</b>")
    else:
        await message.answer("<b>❌ НЕТ ДОСТУПА</b>")

@admin_dp.message()
async def admin_debug(message: types.Message):
    logging.info(f"Админ-бот получил сообщение от {message.from_user.id}: {message.text}")

# --- ЮЗЕР БОТ: КОМАНДЫ ---
@user_dp.message(Command("start"))
async def user_cmd_start(message: types.Message):
    logging.info(f"Юзер-бот: /start от {message.from_user.id}")
    await message.answer("<b>🎬 ПРИВЕТ! ПРИШЛИ ЭДИТ, И Я ОТПРАВЛЮ ЕГО АДМИНАМ!</b>")

# --- ЮЗЕР БОТ: ПРИЕМ ЭДИТОВ ---
@user_dp.message(F.video | F.animation | F.document)
async def handle_edit(message: types.Message):
    uid = message.from_user.id
    uname = message.from_user.username
    creator = f"@{uname}" if uname else f"ID {uid}"
    logging.info(f"Получен эдит от {uid} ({creator})")

    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="✅ ПРИНЯТЬ", callback_data=f"ok_{uid}"))
    kb.row(types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"no_{uid}"))

    text = (
        f"<b>🎬 НОВЫЙ ЭДИТ!\n"
        f"👤 СОЗДАТЕЛЬ — {creator}\n"
        f"⏳ ОЖИДАЕТ ПРОВЕРКИ\n"
        f"ПРИНЯТЬ ИЛИ ОТКЛОНИТЬ?</b>"
    )

    sent_count = 0
    for admin_id in ADMIN_IDS:
        try:
            await user_bot.forward_message(
                chat_id=admin_id,
                from_chat_id=message.chat.id,
                message_id=message.message_id
            )
            await admin_bot.send_message(
                admin_id,
                text,
                reply_markup=kb.as_markup()
            )
            sent_count += 1
            logging.info(f"Эдит успешно отправлен админу {admin_id}")
        except Exception as e:
            logging.error(f"Ошибка отправки админу {admin_id}: {e}")

    if sent_count > 0:
        await message.answer("<b>🚀 ТВОЙ ЭДИТ ОТПРАВЛЕН НА ПРОВЕРКУ!\n⏳ ОЖИДАЙ РЕШЕНИЯ АДМИНОВ.</b>")
    else:
        await message.answer("<b>⚠️ ПРОИЗОШЛА ОШИБКА. ПОПРОБУЙ ПОЗЖЕ.</b>")

# --- АДМИН БОТ: КНОПКИ ---
@admin_dp.callback_query(F.data.startswith("ok_") | F.data.startswith("no_"))
async def process_decision(callback: types.CallbackQuery):
    logging.info(f"Callback от {callback.from_user.id}: {callback.data}")

    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ НЕТ ДОСТУПА", show_alert=True)
        return

    action, user_id = callback.data.split("_", 1)
    admin_name = callback.from_user.first_name or "Админ"

    if action == "ok":
        try:
            await admin_bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id - 1,
                caption=f"<b>🔥 ЭДИТ В КАНАЛЕ!\nАВТОР: <a href='tg://user?id={user_id}'>МАСТЕР</a></b>"
            )
            await callback.message.edit_text(
                text=f"<b>✅ ПРИНЯТО!\n👤 РЕШЕНИЕ: {admin_name}</b>"
            )
            await user_bot.send_message(
                int(user_id),
                "<b>🌟 ТВОЙ ЭДИТ ОПУБЛИКОВАН В КАНАЛЕ!\n🔥 КРАСАВЧИК!</b>"
            )
            logging.info(f"Эдит от {user_id} принят и опубликован")
        except Exception as e:
            logging.error(f"Ошибка при принятии: {e}")
            await callback.answer(f"ОШИБКА: {e}", show_alert=True)
            return
    else:
        try:
            await callback.message.edit_text(
                text=f"<b>❌ ОТКЛОНЕНО.\n👤 РЕШЕНИЕ: {admin_name}</b>"
            )
            await user_bot.send_message(
                int(user_id),
                "<b>😔 ТВОЙ ЭДИТ ОТКЛОНЁН.\nПОПРОБУЙ ПРИСЛАТЬ ДРУГОЙ!</b>"
            )
            logging.info(f"Эдит от {user_id} отклонён")
        except Exception as e:
            logging.warning(f"Ошибка при отклонении: {e}")

    await callback.answer()

# --- ЗАПУСК ---
async def main():
    await run_server()
    logging.info("Запускаем polling...")
    await notify_admins_on_start()
    await asyncio.gather(
        admin_dp.start_polling(admin_bot, skip_updates=True),
        user_dp.start_polling(user_bot, skip_updates=True),
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("STOPPED")
