"""Сборка диспетчера aiogram 3."""

from __future__ import annotations

from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from telegram_bot.gateway import AsyncWeatherGateway
from telegram_bot.handlers import build_router


def create_dispatcher(gateway: AsyncWeatherGateway) -> Dispatcher:
    """Создаёт диспетчер с памятью FSM и шлюзом погоды в данных обработчиков.

    Шлюз общий и не хранит шаг пользователя. Шаг лежит в MemoryStorage
    и читается через FSMContext внутри конкретного апдейта.
    """

    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher["gateway"] = gateway
    dispatcher.include_router(build_router())
    return dispatcher
