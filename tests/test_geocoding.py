"""Прямой и обратный геокодинг."""

from __future__ import annotations

import pytest

from services.weather_service import WeatherService
from tests.http_fakes import FakeResponse, FakeSession
from tests.payloads import geo_payload
from weather_api.client import GEO_ROOT, OpenWeatherClient
from weather_api.exceptions import ValidationError, WeatherResponseError


def test_direct_geocoding_prefers_russian_name_and_skips_units() -> None:
    session = FakeSession(FakeResponse(200, geo_payload()))
    client = OpenWeatherClient("super-secret-key", session=session)

    places = client.geocode_direct("Moscow", limit=5)

    assert places[0].name == "Москва"
    assert places[0].country == "RU"
    assert places[0].lat == pytest.approx(55.7504461)
    call = session.calls[0]
    assert call["url"] == f"{GEO_ROOT}/direct"
    assert call["params"]["q"] == "Moscow"
    assert call["params"]["limit"] == 5
    assert "units" not in call["params"]
    assert "lang" not in call["params"]
    assert "super-secret-key" not in call["url"]


def test_reverse_geocoding_by_coordinates() -> None:
    session = FakeSession(FakeResponse(200, geo_payload()))
    client = OpenWeatherClient("super-secret-key", session=session)

    places = client.geocode_reverse(55.75, 37.62, limit=1)

    assert places[0].name == "Москва"
    assert session.calls[0]["url"] == f"{GEO_ROOT}/reverse"
    assert session.calls[0]["params"]["lat"] == 55.75
    assert session.calls[0]["params"]["lon"] == 37.62


def test_empty_geocode_list_is_a_normal_result() -> None:
    session = FakeSession(FakeResponse(200, []))
    client = OpenWeatherClient("super-secret-key", session=session)

    assert client.geocode_direct("Атлантида") == []


def test_geocode_object_instead_of_list_is_rejected() -> None:
    session = FakeSession(FakeResponse(200, {"cod": 200}))
    client = OpenWeatherClient("super-secret-key", session=session)

    with pytest.raises(WeatherResponseError):
        client.geocode_direct("Москва")


def test_service_chooses_direct_or_reverse_query() -> None:
    def responder(call: dict[str, object]) -> FakeResponse:
        if str(call["url"]).endswith("/direct"):
            return FakeResponse(200, geo_payload())
        return FakeResponse(200, geo_payload())

    session = FakeSession(responder)
    service = WeatherService(OpenWeatherClient("super-secret-key", session=session))

    by_city = service.geocode("Санкт-Петербург")
    by_point = service.geocode("55.7558, 37.6173")

    assert by_city[0].name == "Москва"
    assert by_point[0].name == "Москва"
    assert session.calls[0]["url"].endswith("/direct")
    assert session.calls[1]["url"].endswith("/reverse")


def test_invalid_coordinates_do_not_call_http() -> None:
    session = FakeSession(FakeResponse(200, geo_payload()))
    service = WeatherService(OpenWeatherClient("super-secret-key", session=session))

    with pytest.raises(ValidationError):
        service.geocode("91, 10")

    assert session.calls == []
