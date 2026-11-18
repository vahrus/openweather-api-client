"""Синхронный сервис не вызывается прямо из event loop."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from telegram_bot import gateway as gateway_module
from telegram_bot.gateway import AsyncWeatherGateway
from tests.samples import moscow_weather


@pytest.mark.asyncio
async def test_gateway_offloads_requests_with_to_thread(monkeypatch: pytest.MonkeyPatch) -> None:
    service = MagicMock()
    service.current_by_city.return_value = moscow_weather()
    seen: dict[str, object] = {}

    async def fake_to_thread(func, *args, **kwargs):
        seen["func"] = func
        seen["args"] = args
        seen["kwargs"] = kwargs
        return func(*args, **kwargs)

    monkeypatch.setattr(gateway_module.asyncio, "to_thread", fake_to_thread)
    gateway = AsyncWeatherGateway(service)

    weather = await gateway.current_by_city("Москва")

    assert weather.city == "Москва"
    assert seen["func"] == service.current_by_city
    assert seen["args"] == ("Москва",)
