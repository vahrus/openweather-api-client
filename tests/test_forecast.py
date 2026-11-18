"""Прогноз на 5 дней и группировка по локальным суткам."""

from __future__ import annotations

from datetime import timedelta

import pytest

from services.formatters import format_forecast, summarize_daily
from tests.http_fakes import FakeResponse, FakeSession
from tests.payloads import forecast_payload
from tests.samples import sample_forecast
from weather_api.client import OpenWeatherClient


def test_forecast_request_and_local_timezone() -> None:
    session = FakeSession(FakeResponse(200, forecast_payload()))
    client = OpenWeatherClient("super-secret-key", session=session)

    forecast = client.get_forecast_by_city("Казань")

    assert forecast.city == "Казань"
    assert forecast.timezone_offset_seconds == 10800
    assert len(forecast.slots) == 3
    assert all(slot.moment.utcoffset() == timedelta(hours=3) for slot in forecast.slots)
    assert session.calls[0]["url"].endswith("/data/2.5/forecast")
    assert session.calls[0]["params"]["units"] == "metric"
    assert session.calls[0]["params"]["lang"] == "ru"
    assert "appid" not in session.calls[0]["url"]


def test_daily_summary_splits_local_midnight() -> None:
    days = summarize_daily(sample_forecast())

    assert len(days) == 2
    assert days[0].day.strftime("%d.%m") == "01.06"
    assert days[0].temp_min_c == 10
    assert days[0].temp_max_c == 20
    assert days[0].midday_temp_c == 10
    assert days[0].description == "Ясно"
    assert days[0].pop_max == pytest.approx(0.4)
    assert days[1].day.strftime("%d.%m") == "02.06"
    assert days[1].temp_min_c == 5
    assert days[1].description == "Дождь"


def test_forecast_text_mentions_three_hour_step_and_timezone() -> None:
    text = format_forecast(sample_forecast())

    assert "Прогноз на 5 дней: Казань, RU" in text
    assert "UTC+3" in text
    assert "3 часа" in text
    assert "01.06" in text
    assert "02.06" in text
    assert "осадки до 40%" in text
    assert "осадки до 90%" in text
