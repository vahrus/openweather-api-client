"""Ошибки HTTP, проверка ввода и безопасные тексты."""

from __future__ import annotations

import pytest
import requests

from services.weather_service import WeatherService
from tests.http_fakes import FakeResponse, FakeSession
from tests.payloads import current_payload
from weather_api.client import OpenWeatherClient
from weather_api.exceptions import (
    ValidationError,
    WeatherAPIError,
    WeatherAuthError,
    WeatherNetworkError,
    WeatherNotFoundError,
    WeatherRateLimitError,
    WeatherResponseError,
    WeatherServerError,
)
from weather_api.validation import parse_coordinates, validate_city


def _client(response: FakeResponse | Exception) -> tuple[OpenWeatherClient, FakeSession]:
    session = FakeSession(response)
    return OpenWeatherClient("super-secret-key", session=session), session


@pytest.mark.parametrize(
    ("status", "error_type"),
    [
        (401, WeatherAuthError),
        (404, WeatherNotFoundError),
        (429, WeatherRateLimitError),
        (500, WeatherServerError),
        (502, WeatherServerError),
        (302, WeatherAPIError),
        (400, WeatherAPIError),
    ],
)
def test_http_statuses(status: int, error_type: type[WeatherAPIError]) -> None:
    client, _session = _client(FakeResponse(status, {"cod": status, "message": "appid=super-secret-key"}))

    with pytest.raises(error_type) as caught:
        client.get_current_weather_by_city("Москва")

    assert "super-secret-key" not in str(caught.value)
    assert "http://" not in str(caught.value).lower()
    assert "https://" not in str(caught.value).lower()


def test_embedded_404_inside_http_200() -> None:
    client, _session = _client(FakeResponse(200, {"cod": "404", "message": "city not found"}))

    with pytest.raises(WeatherNotFoundError):
        client.get_current_weather_by_city("Москва")


def test_coordinates_404_has_its_own_text() -> None:
    client, _session = _client(FakeResponse(404, {"cod": "404"}))

    with pytest.raises(WeatherNotFoundError, match="координат"):
        client.get_current_weather_by_coords(10, 20)


def test_invalid_json_and_empty_body() -> None:
    client, _session = _client(FakeResponse(200, "not-json"))
    with pytest.raises(WeatherResponseError):
        client.get_current_weather_by_city("Москва")

    broken, _session = _client(FakeResponse(200, {}))
    with pytest.raises(WeatherResponseError):
        broken.get_current_weather_by_city("Москва")


def test_auth_error_without_json_body() -> None:
    client, _session = _client(FakeResponse(401, ""))

    with pytest.raises(WeatherAuthError) as caught:
        client.get_current_weather_by_city("Москва")

    assert "super-secret-key" not in str(caught.value)


def test_place_lookup_failure_still_returns_weather() -> None:
    def responder(call: dict[str, object]) -> FakeResponse:
        if str(call["url"]).endswith("/weather"):
            return FakeResponse(200, current_payload())
        return FakeResponse(503, "down")

    session = FakeSession(responder)
    service = WeatherService(OpenWeatherClient("super-secret-key", session=session))

    places, weather = service.place_and_weather(55.75, 37.62)

    assert places == []
    assert weather.city == "Москва"
    assert len(session.calls) == 2


def test_timeout_is_network_error() -> None:
    client, _session = _client(requests.Timeout("appid=super-secret-key"))

    with pytest.raises(WeatherNetworkError) as caught:
        client.get_forecast_by_city("Москва")

    assert "super-secret-key" not in str(caught.value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("  Москва  ", "Москва"),
        ("Санкт-Петербург", "Санкт-Петербург"),
        ("Ростов-на-Дону", "Ростов-на-Дону"),
        ("New York", "New York"),
        ("Москва, RU", "Москва, RU"),
    ],
)
def test_valid_cities(value: str, expected: str) -> None:
    assert validate_city(value) == expected


@pytest.mark.parametrize("value", ["", "   ", "Москва!", "город\nимя", "a" * 81, "<script>"])
def test_invalid_cities(value: str) -> None:
    with pytest.raises(ValidationError):
        validate_city(value)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("55.7558, 37.6173", (55.7558, 37.6173)),
        ("55.7558,37.6173", (55.7558, 37.6173)),
        ("-33.8688 151.2093", (-33.8688, 151.2093)),
        ("55.75; -37.6", (55.75, -37.6)),
    ],
)
def test_valid_coordinates(value: str, expected: tuple[float, float]) -> None:
    lat, lon = parse_coordinates(value)
    assert lat == pytest.approx(expected[0])
    assert lon == pytest.approx(expected[1])


@pytest.mark.parametrize("value", ["", "Москва", "91, 0", "10, 181", "55.7", "abc, def", "nan, 0"])
def test_invalid_coordinates(value: str) -> None:
    with pytest.raises(ValidationError):
        parse_coordinates(value)
