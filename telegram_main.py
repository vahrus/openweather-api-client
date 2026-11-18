"""Запуск Telegram-бота long polling.

Из корня проекта: python telegram_main.py
Нужны OPENWEATHER_API_KEY и TELEGRAM_BOT_TOKEN в окружении или в .env.
"""

from __future__ import annotations

import asyncio
import logging
import os

from aiogram import Bot
from aiogram.utils.token import TokenValidationError
from dotenv import load_dotenv

from services.weather_service import WeatherService
from telegram_bot.bot import create_dispatcher
from telegram_bot.gateway import AsyncWeatherGateway
from weather_api.client import OpenWeatherClient
from weather_api.logging_utils import setup_logging

logger = logging.getLogger("telegram_main")


def main() -> int:
    """Проверяет окружение и запускает long polling."""

    load_dotenv()
    setup_logging()
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not api_key or not token:
        logger.error("Задайте OPENWEATHER_API_KEY и TELEGRAM_BOT_TOKEN в файле .env")
        return 1

    client = OpenWeatherClient(api_key)
    gateway = AsyncWeatherGateway(WeatherService(client))
    try:
        bot = Bot(token=token)
    except TokenValidationError:
        logger.error("TELEGRAM_BOT_TOKEN имеет неверный формат")
        client.close()
        return 1

    dispatcher = create_dispatcher(gateway)
    try:
        asyncio.run(dispatcher.start_polling(bot))
    finally:
        client.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
