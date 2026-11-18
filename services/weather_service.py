"""Сценарии приложения поверх HTTP-клиента."""

from __future__ import annotations

import logging

from weather_api.client import OpenWeatherClient
from weather_api.exceptions import ValidationError, WeatherAPIError, WeatherNotFoundError
from weather_api.models import AirQuality, CurrentWeather, Forecast, GeoLocation
from weather_api.validation import looks_like_coordinates, parse_coordinates, validate_city

logger = logging.getLogger(__name__)


class WeatherService:
    """Бизнес-операции, общие для консоли и Telegram-бота."""

    def __init__(self, client: OpenWeatherClient) -> None:
        self._client = client

    def current_by_city(self, city: str) -> CurrentWeather:
        """Текущая погода, включая давление, видимость, восход и закат."""

        return self._client.get_current_weather_by_city(city)

    def forecast_by_city(self, city: str) -> Forecast:
        """Прогноз на 5 дней с шагом 3 часа."""

        return self._client.get_forecast_by_city(city)

    def geocode(self, query: str) -> list[GeoLocation]:
        """Прямой геокодинг города или обратный — если введены координаты."""

        if looks_like_coordinates(query):
            lat, lon = parse_coordinates(query)
            return self._client.geocode_reverse(lat, lon, limit=5)
        return self._client.geocode_direct(query, limit=5)

    def current_by_coordinates(self, lat: float, lon: float) -> CurrentWeather:
        """Текущая погода по уже разобранным координатам."""

        return self._client.get_current_weather_by_coords(lat, lon)

    def place_and_weather(self, lat: float, lon: float) -> tuple[list[GeoLocation], CurrentWeather]:
        """Погода по координатам и ближайшее место по обратному геокодингу."""

        weather = self.current_by_coordinates(lat, lon)
        try:
            places = self._client.geocode_reverse(lat, lon, limit=1)
        except WeatherAPIError:
            logger.warning("Обратный геокодинг недоступен, показана только погода")
            places = []
        return places, weather

    def air_by_city(self, city: str) -> tuple[GeoLocation, AirQuality]:
        """Качество воздуха: город сначала переводится в координаты."""

        cleaned = validate_city(city)
        locations = self._client.geocode_direct(cleaned, limit=1)
        if not locations:
            raise WeatherNotFoundError(f"Город «{cleaned}» не найден.")
        location = locations[0]
        air = self._client.get_air_pollution(location.lat, location.lon)
        return location, air

    def compare_cities(self, first: str, second: str) -> tuple[CurrentWeather, CurrentWeather]:
        """Сравнивает текущую погоду двух разных городов."""

        left_name = validate_city(first)
        right_name = validate_city(second)
        if left_name.casefold() == right_name.casefold():
            raise ValidationError("Для сравнения нужны два разных города.")
        left = self._client.get_current_weather_by_city(left_name)
        right = self._client.get_current_weather_by_city(right_name)
        return left, right
