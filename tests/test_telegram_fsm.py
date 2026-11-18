"""Переходы FSM, отмена сценария и кнопки из чужого состояния."""

from __future__ import annotations

import pytest
from aiogram.types import Location

from telegram_bot.keyboards import BTN_FORECAST, BTN_MENU, BTN_WEATHER
from telegram_bot.states import WeatherStates
from tests.conftest import BotHarness
from tests.telegram_utils import fsm_snapshot, last_text


async def _state(app: BotHarness) -> tuple[str | None, dict[str, object]]:
    return await fsm_snapshot(app.dispatcher, app.bot.id)


@pytest.mark.asyncio
async def test_weather_command_and_city_then_clear(app: BotHarness) -> None:
    await app.send("/weather")
    state, data = await _state(app)
    assert state == WeatherStates.waiting_weather_city.state
    assert data == {}

    await app.send("Москва")
    state, data = await _state(app)
    assert state is None
    assert data == {}
    assert app.gateway.calls == [("current", "Москва")]
    assert "Москва" in last_text(app.session)


@pytest.mark.asyncio
async def test_commands_and_buttons_work_from_another_state(app: BotHarness) -> None:
    await app.send("/compare")
    await app.send("Москва")
    state, data = await _state(app)
    assert state == WeatherStates.waiting_compare_second_city.state
    assert data["compare_first_city"] == "Москва"

    await app.send(BTN_FORECAST)
    state, data = await _state(app)
    assert state == WeatherStates.waiting_forecast_city.state
    assert data == {}
    assert app.gateway.calls == []

    await app.send("/weather")
    state, _data = await _state(app)
    assert state == WeatherStates.waiting_weather_city.state
    assert "город" in last_text(app.session).lower()


@pytest.mark.asyncio
async def test_cancel_drops_compare_scenario(app: BotHarness) -> None:
    await app.send("/compare")
    await app.send("Москва")
    await app.send("/cancel")

    state, data = await _state(app)
    assert state is None
    assert data == {}
    assert "отменено" in last_text(app.session).lower()

    await app.send("Казань")
    assert app.gateway.calls == []
    state, data = await _state(app)
    assert state is None
    assert data == {}
    assert "справка" in last_text(app.session).lower()


@pytest.mark.asyncio
async def test_main_menu_button_cancels_scenario(app: BotHarness) -> None:
    await app.send(BTN_WEATHER)
    await app.send(BTN_MENU)

    state, data = await _state(app)
    assert state is None
    assert data == {}
    assert "Главное меню" in last_text(app.session)


@pytest.mark.asyncio
async def test_help_keeps_current_state(app: BotHarness) -> None:
    await app.send("/air")
    await app.send("/help")

    state, _data = await _state(app)
    assert state == WeatherStates.waiting_air_city.state
    assert "/cancel" in last_text(app.session)


@pytest.mark.asyncio
async def test_location_and_text_coordinates_are_not_stored(app: BotHarness) -> None:
    await app.send("/geo")
    state, _data = await _state(app)
    assert state == WeatherStates.waiting_geo.state

    await app.send(location=Location(latitude=55.7558, longitude=37.6173))
    state, data = await _state(app)
    assert state is None
    assert data == {}
    assert app.gateway.calls == [("place", 55.7558, 37.6173)]

    await app.send("/geo")
    await app.send("55.7558, 37.6173")
    assert app.gateway.calls[-1] == ("place", 55.7558, 37.6173)
    state, data = await _state(app)
    assert state is None
    assert "lat" not in data
    assert "55.7558" not in data.values()


@pytest.mark.asyncio
async def test_live_location_is_rejected(app: BotHarness) -> None:
    await app.send("/geo")
    await app.send(location=Location(latitude=55.75, longitude=37.61, live_period=60))

    state, data = await _state(app)
    assert state == WeatherStates.waiting_geo.state
    assert data == {}
    assert app.gateway.calls == []
    assert "постоянная геолокация" in last_text(app.session).lower()


@pytest.mark.asyncio
async def test_unknown_command_does_not_leave_the_state(app: BotHarness) -> None:
    await app.send("/weather")
    await app.send("/no-such-command")

    state, _data = await _state(app)
    assert state == WeatherStates.waiting_weather_city.state
    assert app.gateway.calls == []
    assert "/cancel" in last_text(app.session)
