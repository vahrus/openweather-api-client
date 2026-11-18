"""Асинхронный доступ к синхронному клиенту OpenWeatherMap.

requests блокирует поток, поэтому обработчики aiogram не вызывают HTTP сами.
Ожидание вынесено в asyncio.to_thread на этом слое.
"""

from __future__ import annotations

import asyncio

from services.weather_service import WeatherService
from weather_api.models import AirQuality, CurrentWeather, Forecast, GeoLocation


class AsyncWeatherGateway:
    """Фасад сервиса погоды для async-обработчиков."""

    def __init__(self, service: WeatherService) -> None:
        self._service = service

    async def current_by_city(self, city: str) -> CurrentWeather:
        """Текущая погода по городу в отдельном потоке."""

        return await asyncio.to_thread(self._service.current_by_city, city)

    async def forecast_by_city(self, city: str) -> Forecast:
        """Прогноз на 5 дней в отдельном потоке."""

        return await asyncio.to_thread(self._service.forecast_by_city, city)

    async def place_and_weather(
        self, lat: float, lon: float
    ) -> tuple[list[GeoLocation], CurrentWeather]:
        """Погода и обратный геокодинг по координатам в отдельном потоке."""

        return await asyncio.to_thread(self._service.place_and_weather, lat, lon)

    async def air_by_city(self, city: str) -> tuple[GeoLocation, AirQuality]:
        """Качество воздуха по городу в отдельном потоке."""

        return await asyncio.to_thread(self._service.air_by_city, city)

    async def compare_cities(self, first: str, second: str) -> tuple[CurrentWeather, CurrentWeather]:
        """Сравнение двух городов в отдельном потоке."""

        return await asyncio.to_thread(self._service.compare_cities, first, second)
