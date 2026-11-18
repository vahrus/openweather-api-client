"""Разбор JSON OpenWeatherMap в модели приложения."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from weather_api.exceptions import WeatherResponseError
from weather_api.models import AirQuality, CurrentWeather, Forecast, ForecastSlot, GeoLocation

_AQI_MIN = 1
_AQI_MAX = 5


def _as_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WeatherResponseError(f"Некорректный JSON OpenWeatherMap ({context}).")
    return value


def _require_number(mapping: dict[str, Any], key: str, context: str) -> float:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise WeatherResponseError(f"В ответе нет числа «{key}» ({context}).")
    return float(value)


def _optional_number(mapping: dict[str, Any], key: str) -> float | None:
    value = mapping.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return int(value)


def _timezone(offset_seconds: int) -> timezone:
    return timezone(timedelta(seconds=offset_seconds))


def _aware(timestamp: Any, offset_seconds: int) -> datetime | None:
    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
        return None
    return datetime.fromtimestamp(int(timestamp), tz=_timezone(offset_seconds))


def _description(raw: dict[str, Any]) -> str:
    weather = raw.get("weather")
    if not isinstance(weather, list):
        raise WeatherResponseError("В ответе нет описания погоды.")
    parts: list[str] = []
    for item in weather:
        if isinstance(item, dict):
            text = str(item.get("description") or "").strip()
            if text:
                parts.append(text)
    if not parts:
        raise WeatherResponseError("В ответе нет описания погоды.")
    return ", ".join(parts)


def _offset(raw: dict[str, Any], nested: dict[str, Any] | None = None) -> int:
    source = nested if nested is not None else raw
    value = source.get("timezone", raw.get("timezone", 0))
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return 0
    return int(value)


def parse_current_weather(payload: Any) -> CurrentWeather:
    """Собирает текущую погоду из ответа `/data/2.5/weather`."""

    raw = _as_mapping(payload, "текущая погода")
    main = raw.get("main")
    if not isinstance(main, dict):
        raise WeatherResponseError("В ответе нет блока main.")
    coord = raw.get("coord") if isinstance(raw.get("coord"), dict) else {}
    sys_block = raw.get("sys") if isinstance(raw.get("sys"), dict) else {}
    wind = raw.get("wind") if isinstance(raw.get("wind"), dict) else {}
    clouds = raw.get("clouds") if isinstance(raw.get("clouds"), dict) else {}
    offset = _offset(raw)
    city = str(raw.get("name") or "").strip() or "Без названия"
    return CurrentWeather(
        city=city,
        country=str(sys_block.get("country") or "").strip(),
        lat=float(coord.get("lat") or 0),
        lon=float(coord.get("lon") or 0),
        temp_c=_require_number(main, "temp", "текущая погода"),
        feels_like_c=_optional_number(main, "feels_like"),
        humidity_percent=_optional_int(main.get("humidity")),
        description=_description(raw),
        wind_speed_ms=_optional_number(wind, "speed"),
        pressure_hpa=_optional_int(main.get("pressure")),
        visibility_m=_optional_int(raw.get("visibility")),
        sunrise=_aware(sys_block.get("sunrise"), offset),
        sunset=_aware(sys_block.get("sunset"), offset),
        timezone_offset_seconds=offset,
        clouds_percent=_optional_int(clouds.get("all")),
    )


def _parse_slot(raw: Any, offset_seconds: int) -> ForecastSlot:
    item = _as_mapping(raw, "шаг прогноза")
    main = item.get("main")
    if not isinstance(main, dict):
        raise WeatherResponseError("В шаге прогноза нет блока main.")
    wind = item.get("wind") if isinstance(item.get("wind"), dict) else {}
    moment = _aware(item.get("dt"), offset_seconds)
    if moment is None:
        raise WeatherResponseError("В шаге прогноза нет времени.")
    pop_raw = item.get("pop", 0)
    pop = float(pop_raw) if isinstance(pop_raw, (int, float)) and not isinstance(pop_raw, bool) else 0.0
    pop = min(1.0, max(0.0, pop))
    return ForecastSlot(
        moment=moment,
        temp_c=_require_number(main, "temp", "прогноз"),
        feels_like_c=_optional_number(main, "feels_like"),
        humidity_percent=_optional_int(main.get("humidity")),
        description=_description(item),
        wind_speed_ms=_optional_number(wind, "speed"),
        pop=pop,
        pressure_hpa=_optional_int(main.get("pressure")),
    )


def parse_forecast(payload: Any) -> Forecast:
    """Собирает прогноз из ответа `/data/2.5/forecast`."""

    raw = _as_mapping(payload, "прогноз")
    city_block = raw.get("city") if isinstance(raw.get("city"), dict) else {}
    coord = city_block.get("coord") if isinstance(city_block.get("coord"), dict) else {}
    slots_raw = raw.get("list")
    if not isinstance(slots_raw, list) or not slots_raw:
        raise WeatherResponseError("В прогнозе нет списка интервалов.")
    offset = _offset(raw, city_block)
    slots = [_parse_slot(item, offset) for item in slots_raw]
    city = str(city_block.get("name") or "").strip() or "Без названия"
    return Forecast(
        city=city,
        country=str(city_block.get("country") or "").strip(),
        lat=float(coord.get("lat") or 0),
        lon=float(coord.get("lon") or 0),
        timezone_offset_seconds=offset,
        slots=slots,
    )


def parse_geocode_list(payload: Any) -> list[GeoLocation]:
    """Собирает список мест из прямого или обратного геокодинга."""

    if payload is None:
        raise WeatherResponseError("Геокодинг вернул пустой ответ.")
    if not isinstance(payload, list):
        raise WeatherResponseError("Геокодинг вернул не список.")
    locations: list[GeoLocation] = []
    for item in payload:
        raw = _as_mapping(item, "геокодинг")
        local_names = raw.get("local_names") if isinstance(raw.get("local_names"), dict) else {}
        name = str(local_names.get("ru") or raw.get("name") or "").strip()
        if not name:
            raise WeatherResponseError("В ответе геокодинга нет названия.")
        state = raw.get("state")
        locations.append(
            GeoLocation(
                name=name,
                lat=_require_number(raw, "lat", "геокодинг"),
                lon=_require_number(raw, "lon", "геокодинг"),
                country=str(raw.get("country") or "").strip(),
                state=str(state).strip() if state else None,
            )
        )
    return locations


def parse_air_quality(payload: Any) -> AirQuality:
    """Собирает качество воздуха из ответа `/data/2.5/air_pollution`."""

    raw = _as_mapping(payload, "качество воздуха")
    items = raw.get("list")
    if not isinstance(items, list) or not items:
        raise WeatherResponseError("В ответе нет данных о качестве воздуха.")
    current = _as_mapping(items[0], "качество воздуха")
    main = current.get("main") if isinstance(current.get("main"), dict) else {}
    aqi = _optional_int(main.get("aqi"))
    if aqi is None or not _AQI_MIN <= aqi <= _AQI_MAX:
        raise WeatherResponseError("Индекс AQI отсутствует или выходит за диапазон 1–5.")
    components_raw = current.get("components") if isinstance(current.get("components"), dict) else {}
    components: dict[str, float] = {}
    for key, value in components_raw.items():
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            components[str(key)] = float(value)
    moment = _aware(current.get("dt"), 0)
    if moment is None:
        raise WeatherResponseError("В данных о воздухе нет отметки времени.")
    coord = raw.get("coord") if isinstance(raw.get("coord"), dict) else {}
    return AirQuality(
        lat=float(coord.get("lat") or 0),
        lon=float(coord.get("lon") or 0),
        aqi=aqi,
        components=components,
        moment=moment,
    )
