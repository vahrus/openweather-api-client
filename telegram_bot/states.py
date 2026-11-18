"""Состояния диалога Telegram-бота.

Хранилище aiogram держит шаг отдельно для каждого пользователя.
Глобальная переменная текущего сценария не используется.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup


class WeatherStates(StatesGroup):
    """Шаги, в которых бот ждёт следующий ответ пользователя."""

    waiting_weather_city = State()
    waiting_forecast_city = State()
    waiting_geo = State()
    waiting_compare_first_city = State()
    waiting_compare_second_city = State()
    waiting_air_city = State()
