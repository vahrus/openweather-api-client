"""Команды, кнопки и сообщения об ошибках Telegram-бота."""

from __future__ import annotations

import pytest
from aiogram.methods import SendMessage
from aiogram.types import ReplyKeyboardMarkup

import telegram_main
from telegram_bot.keyboards import (
    BTN_AIR,
    BTN_COMPARE,
    BTN_FORECAST,
    BTN_GEO,
    BTN_HELP,
    BTN_LOCATION,
    BTN_MENU,
    BTN_WEATHER,
    location_keyboard,
    main_menu_keyboard,
)
from telegram_bot.states import WeatherStates
from tests.conftest import BotHarness, make_harness
from tests.telegram_utils import fsm_snapshot, last_text
from weather_api.exceptions import WeatherAuthError, WeatherNotFoundError


def test_main_keyboard_contains_required_buttons() -> None:
    texts = [button.text for row in main_menu_keyboard().keyboard for button in row]

    assert texts == [
        BTN_WEATHER,
        BTN_FORECAST,
        BTN_GEO,
        BTN_COMPARE,
        BTN_AIR,
        BTN_HELP,
        BTN_MENU,
    ]


def test_location_button_requests_one_time_location_only_in_private_chat() -> None:
    private = location_keyboard(private=True)
    location_buttons = [
        button
        for row in private.keyboard
        for button in row
        if button.request_location
    ]
    assert len(location_buttons) == 1
    assert location_buttons[0].text == BTN_LOCATION
    assert location_buttons[0].request_location is True

    public = location_keyboard(private=False)
    assert all(not button.request_location for row in public.keyboard for button in row)
    assert BTN_MENU in [button.text for row in public.keyboard for button in row]


@pytest.mark.asyncio
async def test_start_forecast_compare_and_air(app: BotHarness) -> None:
    await app.send("/start")
    assert "погоды" in last_text(app.session).lower()
    state, _data = await fsm_snapshot(app.dispatcher, app.bot.id)
    assert state is None

    await app.send("/forecast Казань")
    assert app.gateway.calls[-1] == ("forecast", "Казань")
    assert "Прогноз на 5 дней" in last_text(app.session)

    await app.send(BTN_COMPARE)
    await app.send("Москва")
    await app.send("Казань")
    assert app.gateway.calls[-1] == ("compare", "Москва", "Казань")
    assert "теплее" in last_text(app.session)
    state, data = await fsm_snapshot(app.dispatcher, app.bot.id)
    assert state is None
    assert data == {}

    await app.send(BTN_AIR)
    await app.send("Москва")
    assert app.gateway.calls[-1] == ("air", "Москва")
    assert "AQI: 2 из 5" in last_text(app.session)


@pytest.mark.asyncio
async def test_group_geo_does_not_request_location() -> None:
    app = make_harness(chat_type="group")
    try:
        await app.send("/geo")
    finally:
        await app.bot.session.close()

    sent = next(item for item in reversed(app.session.requests) if isinstance(item, SendMessage))
    assert isinstance(sent.reply_markup, ReplyKeyboardMarkup)
    assert all(not button.request_location for row in sent.reply_markup.keyboard for button in row)
    assert "недоступна" in sent.text
    state, _data = await fsm_snapshot(app.dispatcher, app.bot.id)
    assert state == WeatherStates.waiting_geo.state


@pytest.mark.asyncio
async def test_private_geo_keyboard_requests_location(app: BotHarness) -> None:
    await app.send(BTN_GEO)

    sent = next(item for item in reversed(app.session.requests) if isinstance(item, SendMessage))
    assert isinstance(sent.reply_markup, ReplyKeyboardMarkup)
    assert any(button.request_location for row in sent.reply_markup.keyboard for button in row)
    assert "55.7558, 37.6173" in sent.text


@pytest.mark.asyncio
async def test_not_found_keeps_the_prompt_state(app: BotHarness) -> None:
    app.gateway.error = WeatherNotFoundError("Город не найден.")
    await app.send("/weather")
    await app.send("Атлантида")

    state, _data = await fsm_snapshot(app.dispatcher, app.bot.id)
    assert state == WeatherStates.waiting_weather_city.state
    assert "не найден" in last_text(app.session)
    assert "super-secret-key" not in last_text(app.session)


@pytest.mark.asyncio
async def test_auth_error_does_not_reveal_a_key(app: BotHarness) -> None:
    app.gateway.error = WeatherAuthError("appid=super-secret-key")
    await app.send("/weather Москва")

    text = last_text(app.session)
    assert "super-secret-key" not in text
    assert "appid=" not in text
    assert "OPENWEATHER_API_KEY" in text


def test_telegram_main_stops_without_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(telegram_main, "load_dotenv", lambda: False)
    monkeypatch.setattr(telegram_main, "setup_logging", lambda: None)
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)

    assert telegram_main.main() == 1


def test_telegram_main_rejects_malformed_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(telegram_main, "load_dotenv", lambda: False)
    monkeypatch.setattr(telegram_main, "setup_logging", lambda: None)
    monkeypatch.setenv("OPENWEATHER_API_KEY", "test-key")
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "not a token")

    assert telegram_main.main() == 1
