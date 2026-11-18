"""Клиент OpenWeatherMap и модели его ответов."""

from weather_api.client import GEO_ROOT, API_ROOT, OpenWeatherClient
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
from weather_api.models import AirQuality, CurrentWeather, Forecast, ForecastSlot, GeoLocation

__all__ = [
    "API_ROOT",
    "GEO_ROOT",
    "AirQuality",
    "CurrentWeather",
    "Forecast",
    "ForecastSlot",
    "GeoLocation",
    "OpenWeatherClient",
    "ValidationError",
    "WeatherAPIError",
    "WeatherAuthError",
    "WeatherNetworkError",
    "WeatherNotFoundError",
    "WeatherRateLimitError",
    "WeatherResponseError",
    "WeatherServerError",
]
