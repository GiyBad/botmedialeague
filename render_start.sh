#!/bin/bash
# Запускаем микро-сервер, чтобы Render не ругался
uvicorn main:app --host 0.0.0.0 --port $PORT &
# Запускаем самого бота
python bot.py
