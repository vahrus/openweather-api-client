"""Reply-клавиатуры бота.

Кнопка геолокации запрашивает разовую точку только в личном чате.
Постоянный live location не включается.
"""

from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

BTN_WEATHER = "🌤 Погода сейчас"
BTN_FORECAST = "📅 Прогноз на 5 дней"
BTN_GEO = "📍 Геолокация"
BTN_COMPARE = "🏙 Сравнить города"
BTN_AIR = "🌫 Качество воздуха"
BTN_HELP = "ℹ️ Помощь"
BTN_MENU = "🏠 Главное меню"
BTN_LOCATION = "📍 Отправить геолокацию"


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    """Главное меню с командами урока и кнопкой сброса сценария."""

    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text=BTN_WEATHER),
                KeyboardButton(text=BTN_FORECAST),
            ],
            [
                KeyboardButton(text=BTN_GEO),
                KeyboardButton(text=BTN_COMPARE),
            ],
            [
                KeyboardButton(text=BTN_AIR),
                KeyboardButton(text=BTN_HELP),
            ],
            [KeyboardButton(text=BTN_MENU)],
        ],
        resize_keyboard=True,
    )


def location_keyboard(*, private: bool) -> ReplyKeyboardMarkup:
    """Клавиатура геосценария. request_location доступен только в личном чате."""

    rows: list[list[KeyboardButton]] = []
    if private:
        rows.append([KeyboardButton(text=BTN_LOCATION, request_location=True)])
    rows.extend(main_menu_keyboard().keyboard)
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True)
