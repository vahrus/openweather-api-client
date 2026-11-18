"""Общие фикстуры Telegram-тестов. Сеть и настоящие токены не используются."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import pytest
from aiogram import Bot
from aiogram.client.session.base import BaseSession
from aiogram.methods import SendMessage
from aiogram.types import Chat, Message

from telegram_bot.bot import create_dispatcher
from tests.samples import kazan_weather, moscow_location, moscow_weather, sample_air, sample_forecast
from tests.telegram_utils import DUMMY_TOKEN, UpdateFactory
from weather_api.exceptions import WeatherAPIError


class MockSession(BaseSession):
    """Имитирует Telegram Bot API и сохраняет исходящие методы."""

    def __init__(self) -> None:
        super().__init__()
        self.requests: list[object] = []

    async def close(self) -> None:
        return None

    async def make_request(self, bot: Bot, method: object, timeout: int | None = None) -> Message:
        del bot, timeout
        self.requests.append(method)
        if not isinstance(method, SendMessage):
            raise AssertionError(f"Неожиданный метод Telegram: {type(method).__name__}")
        chat_id = method.chat_id if isinstance(method.chat_id, int) else 1
        return Message(
            message_id=len(self.requests),
            date=datetime.now(timezone.utc),
            chat=Chat(id=chat_id, type="private"),
            text=method.text,
        )

    async def stream_content(
        self,
        url: str,
        headers: dict[str, object] | None = None,
        timeout: int = 30,
        chunk_size: int = 65536,
        raise_for_status: bool = True,
    ):
        del url, headers, timeout, chunk_size, raise_for_status
        if False:
            yield b""


class FakeGateway:
    """Шлюз без HTTP: возвращает модели или заранее заданную ошибку."""

    def __init__(self, error: WeatherAPIError | None = None) -> None:
        self.error = error
        self.calls: list[tuple[object, ...]] = []

    async def current_by_city(self, city: str):
        self.calls.append(("current", city))
        if self.error:
            raise self.error
        return moscow_weather()

    async def forecast_by_city(self, city: str):
        self.calls.append(("forecast", city))
        if self.error:
            raise self.error
        return sample_forecast()

    async def place_and_weather(self, lat: float, lon: float):
        self.calls.append(("place", lat, lon))
        if self.error:
            raise self.error
        return [moscow_location()], moscow_weather()

    async def air_by_city(self, city: str):
        self.calls.append(("air", city))
        if self.error:
            raise self.error
        return moscow_location(), sample_air()

    async def compare_cities(self, first: str, second: str):
        self.calls.append(("compare", first, second))
        if self.error:
            raise self.error
        return moscow_weather(), kazan_weather()


@dataclass
class BotHarness:
    bot: Bot
    dispatcher: object
    gateway: FakeGateway
    session: MockSession
    updates: UpdateFactory

    async def send(self, text: str | None = None, location: object | None = None) -> None:
        await self.dispatcher.feed_update(  # type: ignore[attr-defined]
            self.bot,
            self.updates.message(text=text, location=location),  # type: ignore[arg-type]
        )


def make_harness(chat_type: str = "private", error: WeatherAPIError | None = None) -> BotHarness:
    session = MockSession()
    bot = Bot(token=DUMMY_TOKEN, session=session)
    gateway = FakeGateway(error=error)
    dispatcher = create_dispatcher(gateway)  # type: ignore[arg-type]
    return BotHarness(
        bot=bot,
        dispatcher=dispatcher,
        gateway=gateway,
        session=session,
        updates=UpdateFactory(chat_type=chat_type),
    )


@pytest.fixture
async def app() -> BotHarness:
    harness = make_harness()
    try:
        yield harness
    finally:
        await harness.bot.session.close()
