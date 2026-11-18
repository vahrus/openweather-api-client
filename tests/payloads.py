"""Фрагменты JSON OpenWeatherMap для моков HTTP."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def current_payload() -> dict[str, Any]:
    sunrise = int(datetime(2024, 6, 1, 1, 30, tzinfo=timezone.utc).timestamp())
    sunset = int(datetime(2024, 6, 1, 17, 45, tzinfo=timezone.utc).timestamp())
    return {
        "coord": {"lon": 37.6156, "lat": 55.7522},
        "weather": [{"description": "ясно"}],
        "main": {
            "temp": -3.2,
            "feels_like": -7.1,
            "pressure": 1024,
            "humidity": 78,
        },
        "visibility": 10000,
        "wind": {"speed": 4.5},
        "clouds": {"all": 10},
        "sys": {"country": "RU", "sunrise": sunrise, "sunset": sunset},
        "timezone": 10800,
        "name": "Москва",
        "cod": 200,
    }


def forecast_payload() -> dict[str, Any]:
    first = datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc)
    second = datetime(2024, 6, 1, 15, 0, tzinfo=timezone.utc)
    third = datetime(2024, 6, 1, 21, 0, tzinfo=timezone.utc)

    def slot(moment: datetime, temp: float, description: str, pop: float) -> dict[str, Any]:
        return {
            "dt": int(moment.timestamp()),
            "main": {"temp": temp, "feels_like": temp - 1, "humidity": 60, "pressure": 1010},
            "weather": [{"description": description}],
            "wind": {"speed": 3},
            "pop": pop,
        }

    return {
        "city": {
            "name": "Казань",
            "country": "RU",
            "timezone": 10800,
            "coord": {"lat": 55.79, "lon": 49.12},
        },
        "list": [
            slot(first, 10, "ясно", 0.1),
            slot(second, 20, "ясно", 0.4),
            slot(third, 5, "дождь", 0.9),
        ],
        "cod": "200",
    }


def geo_payload() -> list[dict[str, Any]]:
    return [
        {
            "name": "Moscow",
            "local_names": {"ru": "Москва", "en": "Moscow"},
            "lat": 55.7504461,
            "lon": 37.6174943,
            "country": "RU",
            "state": "Moscow",
        }
    ]


def air_payload(aqi: int = 2) -> dict[str, Any]:
    return {
        "coord": {"lon": 37.62, "lat": 55.75},
        "list": [
            {
                "main": {"aqi": aqi},
                "components": {"pm2_5": 8.5, "pm10": 12.25, "co": 201.94},
                "dt": int(datetime(2024, 6, 1, 12, 0, tzinfo=timezone.utc).timestamp()),
            }
        ],
    }
