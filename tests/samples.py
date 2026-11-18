"""Готовые модели для тестов форматирования и Telegram."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from weather_api.models import AirQuality, CurrentWeather, Forecast, ForecastSlot, GeoLocation

ZONE = timezone(timedelta(hours=3))


def moscow_weather() -> CurrentWeather:
    """Зимняя Москва с расширенными полями."""

    return CurrentWeather(
        city="Москва",
        country="RU",
        lat=55.7522,
        lon=37.6156,
        temp_c=-3.2,
        feels_like_c=-7.1,
        humidity_percent=78,
        description="ясно",
        wind_speed_ms=4.5,
        pressure_hpa=1024,
        visibility_m=10000,
        sunrise=datetime(2024, 6, 1, 1, 30, tzinfo=timezone.utc).astimezone(ZONE),
        sunset=datetime(2024, 6, 1, 17, 45, tzinfo=timezone.utc).astimezone(ZONE),
        timezone_offset_seconds=10800,
        clouds_percent=10,
    )


def kazan_weather() -> CurrentWeather:
    """Более тёплая Казань для сравнения."""

    return CurrentWeather(
        city="Казань",
        country="RU",
        lat=55.7887,
        lon=49.1221,
        temp_c=1.5,
        feels_like_c=-1.0,
        humidity_percent=70,
        description="пасмурно",
        wind_speed_ms=2.0,
        pressure_hpa=1012,
        visibility_m=8000,
        sunrise=None,
        sunset=None,
        timezone_offset_seconds=10800,
        clouds_percent=90,
    )


def moscow_location() -> GeoLocation:
    return GeoLocation(name="Москва", lat=55.7522, lon=37.6156, country="RU", state="Москва")


def sample_forecast() -> Forecast:
    return Forecast(
        city="Казань",
        country="RU",
        lat=55.79,
        lon=49.12,
        timezone_offset_seconds=10800,
        slots=[
            ForecastSlot(
                moment=datetime(2024, 6, 1, 15, 0, tzinfo=ZONE),
                temp_c=10,
                feels_like_c=9,
                humidity_percent=60,
                description="ясно",
                wind_speed_ms=3,
                pop=0.1,
                pressure_hpa=1010,
            ),
            ForecastSlot(
                moment=datetime(2024, 6, 1, 18, 0, tzinfo=ZONE),
                temp_c=20,
                feels_like_c=19,
                humidity_percent=55,
                description="ясно",
                wind_speed_ms=3,
                pop=0.4,
                pressure_hpa=1010,
            ),
            ForecastSlot(
                moment=datetime(2024, 6, 2, 0, 0, tzinfo=ZONE),
                temp_c=5,
                feels_like_c=4,
                humidity_percent=80,
                description="дождь",
                wind_speed_ms=5,
                pop=0.9,
                pressure_hpa=1008,
            ),
        ],
    )


def sample_air() -> AirQuality:
    return AirQuality(
        lat=55.7522,
        lon=37.6156,
        aqi=2,
        components={"pm2_5": 8.5, "pm10": 12.25, "no2": 15.0},
        moment=datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc),
    )
