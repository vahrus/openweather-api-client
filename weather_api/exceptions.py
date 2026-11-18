"""Исключения клиента OpenWeatherMap.

Тексты сообщений безопасны для показа пользователю и для логов:
в них нет API-ключей и URL с секретными параметрами.
"""

from __future__ import annotations


class WeatherAPIError(Exception):
    """Базовая ошибка при обращении к OpenWeatherMap."""


class ValidationError(WeatherAPIError):
    """Город или координаты не прошли проверку."""


class WeatherAuthError(WeatherAPIError):
    """API-ключ отсутствует или отклонён (HTTP 401)."""


class WeatherNotFoundError(WeatherAPIError):
    """Город или данные по координатам не найдены (HTTP 404)."""


class WeatherRateLimitError(WeatherAPIError):
    """Превышен лимит запросов (HTTP 429)."""


class WeatherServerError(WeatherAPIError):
    """Сервер OpenWeatherMap недоступен (HTTP 5xx)."""


class WeatherNetworkError(WeatherAPIError):
    """Таймаут или другая сетевая ошибка."""


class WeatherResponseError(WeatherAPIError):
    """Ответ не является ожидаемым JSON или в нём нет нужных полей."""
