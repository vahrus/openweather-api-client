"""HTTP-клиент OpenWeatherMap на requests.Session.

Модуль не знает о Telegram и CLI. В логи попадают только путь и код
ответа: query-параметр appid не записывается.
"""

from __future__ import annotations

import logging
from typing import Any

import requests

from weather_api.exceptions import (
    WeatherAPIError,
    WeatherAuthError,
    WeatherNetworkError,
    WeatherNotFoundError,
    WeatherRateLimitError,
    WeatherResponseError,
    WeatherServerError,
)
from weather_api.models import AirQuality, CurrentWeather, Forecast, GeoLocation
from weather_api.parsers import (
    parse_air_quality,
    parse_current_weather,
    parse_forecast,
    parse_geocode_list,
)
from weather_api.validation import validate_city, validate_coordinates, validate_limit

logger = logging.getLogger(__name__)

API_ROOT = "https://api.openweathermap.org"
GEO_ROOT = "https://api.openweathermap.org/geo/1.0"
USER_AGENT = "openweather-edu-client/1.0"
DEFAULT_TIMEOUT_SECONDS = 10.0


class OpenWeatherClient:
    """Синхронный клиент актуальных endpoint OpenWeatherMap."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        session: requests.Session | None = None,
    ) -> None:
        key = (api_key or "").strip()
        if not key:
            raise WeatherAuthError("Ключ OpenWeatherMap не задан.")
        self._api_key = key
        self._timeout = timeout
        self._owns_session = session is None
        self._session = session or requests.Session()
        self._session.headers["User-Agent"] = USER_AGENT
        self._session.headers["Accept"] = "application/json"

    def __repr__(self) -> str:
        return f"OpenWeatherClient(timeout={self._timeout})"

    def close(self) -> None:
        """Закрывает сессию, если она создана самим клиентом."""

        if self._owns_session:
            self._session.close()
            self._owns_session = False

    def __enter__(self) -> OpenWeatherClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def get_current_weather_by_city(self, city: str) -> CurrentWeather:
        """Текущая погода по названию города."""

        payload = self._request(
            API_ROOT,
            "/data/2.5/weather",
            {"q": validate_city(city), "units": "metric", "lang": "ru"},
        )
        return parse_current_weather(payload)

    def get_current_weather_by_coords(self, lat: float, lon: float) -> CurrentWeather:
        """Текущая погода по широте и долготе."""

        validate_coordinates(lat, lon)
        payload = self._request(
            API_ROOT,
            "/data/2.5/weather",
            {"lat": lat, "lon": lon, "units": "metric", "lang": "ru"},
            by_coords=True,
        )
        return parse_current_weather(payload)

    def get_forecast_by_city(self, city: str) -> Forecast:
        """Прогноз на 5 дней с шагом 3 часа по названию города."""

        payload = self._request(
            API_ROOT,
            "/data/2.5/forecast",
            {"q": validate_city(city), "units": "metric", "lang": "ru"},
        )
        return parse_forecast(payload)

    def get_forecast_by_coords(self, lat: float, lon: float) -> Forecast:
        """Прогноз на 5 дней с шагом 3 часа по координатам."""

        validate_coordinates(lat, lon)
        payload = self._request(
            API_ROOT,
            "/data/2.5/forecast",
            {"lat": lat, "lon": lon, "units": "metric", "lang": "ru"},
            by_coords=True,
        )
        return parse_forecast(payload)

    def geocode_direct(self, city: str, limit: int = 5) -> list[GeoLocation]:
        """Прямой геокодинг: название города -> координаты."""

        payload = self._request(
            GEO_ROOT,
            "/direct",
            {"q": validate_city(city), "limit": validate_limit(limit)},
        )
        return parse_geocode_list(payload)

    def geocode_reverse(self, lat: float, lon: float, limit: int = 1) -> list[GeoLocation]:
        """Обратный геокодинг: координаты -> название места."""

        validate_coordinates(lat, lon)
        payload = self._request(
            GEO_ROOT,
            "/reverse",
            {"lat": lat, "lon": lon, "limit": validate_limit(limit)},
            by_coords=True,
        )
        return parse_geocode_list(payload)

    def get_air_pollution(self, lat: float, lon: float) -> AirQuality:
        """Качество воздуха по координатам. Параметры units и lang endpoint не принимает."""

        validate_coordinates(lat, lon)
        payload = self._request(
            API_ROOT,
            "/data/2.5/air_pollution",
            {"lat": lat, "lon": lon},
            by_coords=True,
        )
        air = parse_air_quality(payload)
        return AirQuality(
            lat=air.lat or lat,
            lon=air.lon or lon,
            aqi=air.aqi,
            components=air.components,
            moment=air.moment,
        )

    def _request(
        self,
        base: str,
        path: str,
        params: dict[str, Any],
        *,
        by_coords: bool = False,
    ) -> Any:
        url = f"{base.rstrip('/')}/{path.lstrip('/')}"
        query = dict(params)
        query["appid"] = self._api_key
        logger.info("Запрос OpenWeather path=%s", path)
        try:
            response = self._session.get(
                url,
                params=query,
                timeout=self._timeout,
                allow_redirects=False,
            )
        except requests.Timeout:
            logger.warning("Таймаут OpenWeather path=%s", path)
            raise WeatherNetworkError(
                "Не удалось дождаться ответа OpenWeatherMap. Повторите запрос."
            ) from None
        except requests.RequestException:
            logger.warning("Сетевая ошибка OpenWeather path=%s", path)
            raise WeatherNetworkError(
                "Нет соединения с OpenWeatherMap. Проверьте сеть и повторите запрос."
            ) from None

        status = int(getattr(response, "status_code", 0) or 0)
        logger.info("Ответ OpenWeather path=%s status=%s", path, status)
        if 300 <= status < 400:
            raise WeatherAPIError("Сервис погоды вернул перенаправление. Запрос остановлен.")
        payload = _read_payload(response)
        _raise_for_status(status, payload, by_coords=by_coords)
        if payload is None:
            raise WeatherResponseError("OpenWeatherMap вернул некорректный JSON.")
        return payload


def _read_payload(response: requests.Response) -> Any:
    text = getattr(response, "text", "") or ""
    if not str(text).strip():
        return None
    try:
        return response.json()
    except ValueError:
        return None


def _body_code(payload: Any) -> int | None:
    if not isinstance(payload, dict) or "cod" not in payload:
        return None
    try:
        return int(payload["cod"])
    except (TypeError, ValueError):
        return None


def _raise_for_status(status: int, payload: Any, *, by_coords: bool) -> None:
    code = status
    embedded = _body_code(payload)
    if status in (200, 201) and embedded is not None and embedded >= 400:
        code = embedded
    if code in (200, 201):
        return
    if code == 401:
        raise WeatherAuthError("Ключ OpenWeatherMap отклонён. Проверьте OPENWEATHER_API_KEY.")
    if code == 404:
        if by_coords:
            raise WeatherNotFoundError("Данные для этих координат не найдены.")
        raise WeatherNotFoundError("Город не найден.")
    if code == 429:
        raise WeatherRateLimitError("Превышен лимит запросов к OpenWeatherMap. Подождите и повторите.")
    if 500 <= code <= 599:
        raise WeatherServerError("Сервис OpenWeatherMap временно недоступен. Повторите запрос позже.")
    raise WeatherAPIError(f"OpenWeatherMap вернул ошибку HTTP {code}.")
