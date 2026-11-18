"""Модели данных OpenWeatherMap.

Температура хранится в градусах Цельсия, скорость ветра — в м/с,
давление — в гектопаскалях, видимость — в метрах.
Время восхода, заката и слотов прогноза — timezone-aware.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
class GeoLocation:
    """Населённый пункт, найденный геокодингом."""

    name: str
    lat: float
    lon: float
    country: str
    state: str | None = None


@dataclass(slots=True)
class CurrentWeather:
    """Текущая погода и расширенные поля наблюдения."""

    city: str
    country: str
    lat: float
    lon: float
    temp_c: float
    feels_like_c: float | None
    humidity_percent: int | None
    description: str
    wind_speed_ms: float | None
    pressure_hpa: int | None
    visibility_m: int | None
    sunrise: datetime | None
    sunset: datetime | None
    timezone_offset_seconds: int
    clouds_percent: int | None = None


@dataclass(slots=True)
class ForecastSlot:
    """Один трёхчасовой шаг прогноза в локальном времени города."""

    moment: datetime
    temp_c: float
    feels_like_c: float | None
    humidity_percent: int | None
    description: str
    wind_speed_ms: float | None
    pop: float
    pressure_hpa: int | None = None


@dataclass(slots=True)
class Forecast:
    """Прогноз на 5 дней с исходным шагом 3 часа."""

    city: str
    country: str
    lat: float
    lon: float
    timezone_offset_seconds: int
    slots: list[ForecastSlot]


@dataclass(slots=True)
class AirQuality:
    """Качество воздуха. Индекс AQI OpenWeather принимает значения 1–5."""

    lat: float
    lon: float
    aqi: int
    components: dict[str, float]
    moment: datetime


@dataclass(slots=True)
class DailySummary:
    """Сводка прогноза за одни локальные сутки."""

    day: datetime
    temp_min_c: float
    temp_max_c: float
    description: str
    pop_max: float
    midday_temp_c: float
