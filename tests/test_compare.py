"""Сравнение текущей погоды двух городов."""

from __future__ import annotations

from dataclasses import replace

import pytest

from services.formatters import format_comparison
from services.weather_service import WeatherService
from tests.http_fakes import FakeResponse, FakeSession
from tests.payloads import current_payload
from tests.samples import kazan_weather, moscow_weather
from weather_api.client import OpenWeatherClient
from weather_api.exceptions import ValidationError


def test_compare_requests_both_cities_and_names_the_warmer_one() -> None:
    def responder(call: dict[str, object]) -> FakeResponse:
        params = call["params"]
        assert isinstance(params, dict)
        payload = current_payload()
        if params["q"] == "Казань":
            payload = current_payload()
            payload["name"] = "Казань"
            payload["main"] = dict(payload["main"])
            payload["main"]["temp"] = 1.5
            payload["coord"] = {"lat": 55.79, "lon": 49.12}
        return FakeResponse(200, payload)

    session = FakeSession(responder)
    service = WeatherService(OpenWeatherClient("super-secret-key", session=session))

    left, right = service.compare_cities("Москва", "Казань")
    text = format_comparison(left, right)

    assert [call["params"]["q"] for call in session.calls] == ["Москва", "Казань"]
    assert left.city == "Москва"
    assert right.temp_c == 1.5
    assert "Сравнение погоды" in text
    assert "В городе Казань теплее на 4.7 °C." in text
    assert "1024 гПа" in text


def test_same_city_is_rejected_without_http() -> None:
    session = FakeSession(FakeResponse(200, current_payload()))
    service = WeatherService(OpenWeatherClient("super-secret-key", session=session))

    with pytest.raises(ValidationError, match="два разных города"):
        service.compare_cities("Москва", " москва ")

    assert session.calls == []


def test_equal_temperature_conclusion() -> None:
    left = moscow_weather()
    right = replace(kazan_weather(), temp_c=left.temp_c)
    text = format_comparison(left, right)

    assert "практически одинаковая" in text
