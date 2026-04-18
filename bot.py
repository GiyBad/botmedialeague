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

# Создаём ОТДЕЛЬНЫЕ диспетчеры для каждого бота
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

# --- ОБРАБОТКА КОМАНД ADMIN БОТА ---
@admin_dp.message(Command("start"))
async def admin_cmd_start(message: types.Message):
    if message.from_user.id in ADMIN_IDS:
        await message.answer("<b>✅ АДМИН-ПАНЕЛЬ ВКЛЮЧЕНА</b>")
    else:
        await message.answer("<b>❌ НЕТ ДОСТУПА</b>")

# --- ОБРАБОТКА КОМАНД USER БОТА ---
@user_dp.message(Command("start"))
async def user_cmd_start(message: types.Message):
    await message.answer("<b>🎬 ПРИВЕТ! ПРИШЛИ ЭДИТ, И Я ОТПРАВЛЮ ЕГО АДМИНАМ!</b>")

# --- ПРИЕМ ЭДИТОВ (только user_dp) ---
@user_dp.message(F.video | F.animation | F.document)
async def handle_edit(message: types.Message):
    uid = message.from_user.id
    uname = message.from_user.username
    creator = f"@{uname}" if uname else f"ID {uid}"

    kb = InlineKeyboardBuilder()
    # FIX: используем строку uid, чтобы потом корректно split('_', 1)
    kb.row(types.InlineKeyboardButton(text="✅ ПРИНЯТЬ", callback_data=f"ok_{uid}"))
    kb.row(types.InlineKeyboardButton(text="❌ ОТКЛОНИТЬ", callback_data=f"no_{uid}"))

    text = f"<b>🎬 НОВЫЙ ЭДИТ!\nСОЗДАТЕЛЬ — {creator}\nПРИНЯТЬ ИЛИ ОТКЛОНИТЬ?</b>"

    for admin_id in ADMIN_IDS:
        try:
            if message.video:
                await admin_bot.send_video(
                    admin_id, message.video.file_id,
                    caption=text, reply_markup=kb.as_markup()
                )
            elif message.animation:
                await admin_bot.send_animation(
                    admin_id, message.animation.file_id,
                    caption=text, reply_markup=kb.as_markup()
                )
            else:
                await admin_bot.send_document(
                    admin_id, message.document.file_id,
                    caption=text, reply_markup=kb.as_markup()
                )
        except Exception as e:
            logging.warning(f"Не удалось отправить эдит админу {admin_id}: {e}")
            continue

    await message.answer("<b>🚀 ТВОЙ ЭДИТ ОТПРАВЛЕН НА ПРОВЕРКУ!</b>")

# --- КНОПКИ (только admin_dp) ---
@admin_dp.callback_query(F.data.startswith("ok_") | F.data.startswith("no_"))
async def process_decision(callback: types.CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("❌ НЕТ ДОСТУПА", show_alert=True)
        return

    # FIX: split('_', 1) — чтобы не сломался при длинном user_id
    action, user_id = callback.data.split("_", 1)

    if action == "ok":
        try:
            await admin_bot.copy_message(
                chat_id=CHANNEL_ID,
                from_chat_id=callback.message.chat.id,
                message_id=callback.message.message_id,
                caption=f"<b>🔥 ЭДИТ В КАНАЛЕ!\nАВТОР: <a href='tg://user?id={user_id}'>МАСТЕР</a></b>"
            )
            await callback.message.edit_caption(caption="<b>✅ ПРИНЯТО!</b>")
            await user_bot.send_message(int(user_id), "<b>🌟 ТВОЙ ЭДИТ ОПУБЛИКОВАН!</b>")
        except Exception as e:
            logging.error(f"Ошибка при принятии эдита: {e}")
            await callback.answer(f"ОШИБКА: {e}", show_alert=True)
            return
    else:
        try:
            await callback.message.edit_caption(caption="<b>❌ ОТКЛОНЕНО.</b>")
            await user_bot.send_message(int(user_id), "<b>😔 ТВОЙ ЭДИТ ОТКЛОНЕН.</b>")
        except Exception as e:
            logging.warning(f"Ошибка при отклонении: {e}")

    await callback.answer()

# --- ЗАПУСК ---
async def main():
    await run_server()  # FIX: await вместо create_task, чтобы сервер точно запустился

    # FIX: запускаем polling для каждого бота в отдельной задаче
    await asyncio.gather(
        admin_dp.start_polling(admin_bot, skip_updates=True),
        user_dp.start_polling(user_bot, skip_updates=True),
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("STOPPED")
