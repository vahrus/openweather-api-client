"""HTTP-клиент с подменой сети."""

from __future__ import annotations

import logging

import pytest
import requests

from tests.http_fakes import FakeResponse, FakeSession
from tests.payloads import current_payload
from weather_api.client import API_ROOT, DEFAULT_TIMEOUT_SECONDS, OpenWeatherClient
from weather_api.exceptions import WeatherAuthError, WeatherNetworkError


def test_current_weather_uses_session_metric_and_russian() -> None:
    session = FakeSession(FakeResponse(200, current_payload()))
    client = OpenWeatherClient("super-secret-key", session=session)

    weather = client.get_current_weather_by_city("Москва")

    assert weather.city == "Москва"
    assert weather.temp_c == -3.2
    assert weather.timezone_offset_seconds == 10800
    assert weather.sunrise is not None
    assert weather.sunrise.utcoffset() is not None
    assert weather.sunrise.strftime("%H:%M") == "04:30"
    call = session.calls[0]
    assert call["url"] == f"{API_ROOT}/data/2.5/weather"
    assert call["params"]["q"] == "Москва"
    assert call["params"]["units"] == "metric"
    assert call["params"]["lang"] == "ru"
    assert call["params"]["appid"] == "super-secret-key"
    assert call["timeout"] == DEFAULT_TIMEOUT_SECONDS
    assert call["allow_redirects"] is False
    assert session.headers["Accept"] == "application/json"


def test_client_does_not_log_api_key(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    session = FakeSession(FakeResponse(200, current_payload()))
    client = OpenWeatherClient("super-secret-key", session=session)

    client.get_current_weather_by_city("Москва")

    logs = "\n".join(record.getMessage() for record in caplog.records)
    assert "super-secret-key" not in logs
    assert "appid=" not in logs
    assert "/data/2.5/weather" in logs


def test_repr_and_external_session_close_hide_the_key() -> None:
    session = FakeSession(FakeResponse(200, current_payload()))
    client = OpenWeatherClient("super-secret-key", session=session)

    assert "super-secret-key" not in repr(client)
    client.close()
    assert session.closed is False


def test_empty_api_key_is_rejected_before_request() -> None:
    with pytest.raises(WeatherAuthError):
        OpenWeatherClient("  ")


def test_network_timeout_and_connection_error_have_no_url() -> None:
    timeout_session = FakeSession(requests.Timeout("timed out appid=super-secret-key"))
    client = OpenWeatherClient("super-secret-key", session=timeout_session)
    with pytest.raises(WeatherNetworkError) as timeout_error:
        client.get_current_weather_by_city("Москва")
    assert "super-secret-key" not in str(timeout_error.value)
    assert "appid" not in str(timeout_error.value)

    connection_session = FakeSession(requests.ConnectionError("failed appid=super-secret-key"))
    client = OpenWeatherClient("super-secret-key", session=connection_session)
    with pytest.raises(WeatherNetworkError) as connection_error:
        client.get_current_weather_by_city("Москва")
    assert "super-secret-key" not in str(connection_error.value)
