"""Качество воздуха и индекс AQI."""

from __future__ import annotations

from datetime import timezone

import pytest

from services.formatters import format_air
from services.weather_service import WeatherService
from tests.http_fakes import FakeResponse, FakeSession
from tests.payloads import air_payload, geo_payload
from weather_api.client import OpenWeatherClient
from weather_api.exceptions import WeatherNotFoundError, WeatherResponseError


def test_air_request_has_no_units_or_language_and_keeps_aqi_scale() -> None:
    session = FakeSession(FakeResponse(200, air_payload(2)))
    client = OpenWeatherClient("super-secret-key", session=session)

    air = client.get_air_pollution(55.75, 37.62)

    assert air.aqi == 2
    assert air.components["pm2_5"] == pytest.approx(8.5)
    assert air.moment.tzinfo == timezone.utc
    params = session.calls[0]["params"]
    assert params["lat"] == 55.75
    assert params["lon"] == 37.62
    assert "units" not in params
    assert "lang" not in params
    assert session.calls[0]["url"].endswith("/data/2.5/air_pollution")


@pytest.mark.parametrize("aqi", [0, 6, None])
def test_aqi_outside_scale_is_rejected(aqi: int | None) -> None:
    payload = air_payload(1)
    if aqi is None:
        del payload["list"][0]["main"]["aqi"]
    else:
        payload["list"][0]["main"]["aqi"] = aqi
    client = OpenWeatherClient("super-secret-key", session=FakeSession(FakeResponse(200, payload)))

    with pytest.raises(WeatherResponseError):
        client.get_air_pollution(55.75, 37.62)


def test_air_by_city_geocodes_then_requests_pollution() -> None:
    def responder(call: dict[str, object]) -> FakeResponse:
        if str(call["url"]).endswith("/direct"):
            return FakeResponse(200, geo_payload())
        return FakeResponse(200, air_payload(4))

    session = FakeSession(responder)
    service = WeatherService(OpenWeatherClient("super-secret-key", session=session))

    location, air = service.air_by_city("Москва")
    text = format_air(location, air)

    assert location.name == "Москва"
    assert air.aqi == 4
    assert session.calls[0]["url"].endswith("/direct")
    assert session.calls[1]["url"].endswith("/air_pollution")
    assert "AQI: 4 из 5 — плохое" in text
    assert "PM2.5: 8.50" in text
    assert "UTC" in text


def test_unknown_city_does_not_request_air() -> None:
    session = FakeSession(FakeResponse(200, []))
    service = WeatherService(OpenWeatherClient("super-secret-key", session=session))

    with pytest.raises(WeatherNotFoundError, match="не найден"):
        service.air_by_city("Атлантида")

    assert len(session.calls) == 1
    assert session.calls[0]["url"].endswith("/direct")
