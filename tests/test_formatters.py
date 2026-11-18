"""Форматирование погоды, давления, видимости и ошибок."""

from __future__ import annotations

import logging

from services.formatters import (
    format_comparison,
    format_current_weather,
    format_locations,
    format_offset,
    format_pressure,
    format_visibility,
    humanize_error,
)
from tests.samples import kazan_weather, moscow_location, moscow_weather
from weather_api.exceptions import (
    ValidationError,
    WeatherAuthError,
    WeatherNetworkError,
    WeatherNotFoundError,
    WeatherRateLimitError,
    WeatherResponseError,
    WeatherServerError,
)
from weather_api.logging_utils import RedactingFormatter


def test_current_weather_shows_extended_fields_and_timezone() -> None:
    text = format_current_weather(moscow_weather())

    assert "Погода: Москва, RU" in text
    assert "-3.2 °C" in text
    assert "Ясно" in text
    assert "78%" in text
    assert "4.5 м/с" in text
    assert "1024 гПа (768 мм рт. ст.)" in text
    assert "10 км" in text
    assert "Восход: 04:30, закат: 20:45 (UTC+3)" in text
    assert "55.7522, 37.6156" in text


def test_units_helpers() -> None:
    assert format_pressure(None) == "нет данных"
    assert format_pressure(1000) == "1000 гПа (750 мм рт. ст.)"
    assert format_visibility(None) == "нет данных"
    assert format_visibility(800) == "800 м"
    assert format_visibility(2500) == "2.5 км"
    assert format_offset(0) == "UTC+0"
    assert format_offset(-18000) == "UTC-5"
    assert format_offset(19800) == "UTC+5:30"


def test_locations_and_equal_cities() -> None:
    assert "Ничего не найдено" in format_locations([])
    listed = format_locations([moscow_location()])
    assert "1. Москва, Москва, RU — 55.7522, 37.6156" in listed
    same = kazan_weather()
    same.temp_c = moscow_weather().temp_c
    assert "практически одинаковая" in format_comparison(moscow_weather(), same)


def test_humanize_hides_secrets_and_explains_status() -> None:
    assert "super-secret-key" not in humanize_error(WeatherAuthError("rejected super-secret-key"))
    assert "OPENWEATHER_API_KEY" in humanize_error(WeatherAuthError("x"))
    assert "не найден" in humanize_error(WeatherNotFoundError("Город не найден."))
    assert "много запросов" in humanize_error(WeatherRateLimitError("429"))
    assert "временно недоступен" in humanize_error(WeatherServerError("500"))
    assert "соединения" in humanize_error(WeatherNetworkError("timeout"))
    assert "непонятный ответ" in humanize_error(WeatherResponseError("json"))
    assert humanize_error(ValidationError("Введите название города.")) == "Введите название города."
    assert "Попробуйте ещё раз" in humanize_error(RuntimeError("boom"))


def test_log_formatter_redacts_appid_and_bot_token() -> None:
    formatter = RedactingFormatter("%(message)s")
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="GET https://api.openweathermap.org/data/2.5/weather?q=Moscow&appid=super-secret-key token=123456:AAEeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee",
        args=(),
        exc_info=None,
    )

    text = formatter.format(record)

    assert "super-secret-key" not in text
    assert "appid=***" in text
    assert "AAEeeeeeeeeeeeeeeeeeeeeeeeeeeeeeeee" not in text
