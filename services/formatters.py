"""Текстовое представление погоды для CLI и Telegram."""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta, timezone

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
from weather_api.models import (
    AirQuality,
    CurrentWeather,
    DailySummary,
    Forecast,
    ForecastSlot,
    GeoLocation,
)

AQI_LABELS: dict[int, str] = {
    1: "хорошее",
    2: "удовлетворительное",
    3: "умеренное",
    4: "плохое",
    5: "очень плохое",
}

COMPONENT_LABELS: dict[str, str] = {
    "co": "CO",
    "no": "NO",
    "no2": "NO2",
    "o3": "O3",
    "so2": "SO2",
    "pm2_5": "PM2.5",
    "pm10": "PM10",
    "nh3": "NH3",
}

_HPA_TO_MMHG = 0.750061683


def format_number(value: float, digits: int = 1) -> str:
    """Форматирует число с фиксированной точностью."""

    return f"{value:.{digits}f}"


def format_offset(seconds: int) -> str:
    """Превращает сдвиг в секундах в подпись вида UTC+3 или UTC+5:30."""

    sign = "+" if seconds >= 0 else "-"
    total = abs(int(seconds))
    hours, remainder = divmod(total, 3600)
    minutes = remainder // 60
    if minutes:
        return f"UTC{sign}{hours}:{minutes:02d}"
    return f"UTC{sign}{hours}"


def format_pressure(hpa: int | None) -> str:
    """Показывает давление в гПа и мм рт. ст."""

    if hpa is None:
        return "нет данных"
    mmhg = round(hpa * _HPA_TO_MMHG)
    return f"{hpa} гПа ({mmhg} мм рт. ст.)"


def format_visibility(meters: int | None) -> str:
    """Показывает видимость в метрах или километрах."""

    if meters is None:
        return "нет данных"
    if meters >= 1000:
        kilometers = meters / 1000
        if kilometers >= 10:
            return f"{kilometers:.0f} км"
        return f"{kilometers:.1f} км"
    return f"{meters} м"


def format_optional_number(value: float | None, suffix: str, digits: int = 1) -> str:
    if value is None:
        return "нет данных"
    return f"{format_number(value, digits)} {suffix}"


def _clock(moment: datetime | None) -> str:
    if moment is None:
        return "нет данных"
    return moment.strftime("%H:%M")


def _capitalize(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return stripped
    return stripped[0].upper() + stripped[1:]


def format_current_weather(weather: CurrentWeather) -> str:
    """Расширенная карточка текущей погоды."""

    humidity = "нет данных" if weather.humidity_percent is None else f"{weather.humidity_percent}%"
    clouds = "нет данных" if weather.clouds_percent is None else f"{weather.clouds_percent}%"
    place = weather.city if not weather.country else f"{weather.city}, {weather.country}"
    lines = [
        f"Погода: {place}",
        f"Координаты: {weather.lat:.4f}, {weather.lon:.4f}",
        f"Сейчас: {format_number(weather.temp_c)} °C, {_capitalize(weather.description)}",
        f"Ощущается как: {format_optional_number(weather.feels_like_c, '°C')}",
        f"Влажность: {humidity}",
        f"Ветер: {format_optional_number(weather.wind_speed_ms, 'м/с')}",
        f"Давление: {format_pressure(weather.pressure_hpa)}",
        f"Облачность: {clouds}",
        f"Видимость: {format_visibility(weather.visibility_m)}",
        (
            f"Восход: {_clock(weather.sunrise)}, закат: {_clock(weather.sunset)} "
            f"({format_offset(weather.timezone_offset_seconds)})"
        ),
    ]
    return "\n".join(lines)


def summarize_daily(forecast: Forecast) -> list[DailySummary]:
    """Группирует трёхчасовые шаги по локальной дате города."""

    grouped: dict[datetime, list[ForecastSlot]] = {}
    order: list[datetime] = []
    for slot in forecast.slots:
        local_day = slot.moment.astimezone(_zone(forecast.timezone_offset_seconds)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        if local_day not in grouped:
            grouped[local_day] = []
            order.append(local_day)
        grouped[local_day].append(slot)

    summaries: list[DailySummary] = []
    for day in order:
        slots = grouped[day]
        temps = [slot.temp_c for slot in slots]
        descriptions = Counter(_capitalize(slot.description) for slot in slots)
        description = descriptions.most_common(1)[0][0]
        midday = min(slots, key=lambda slot: (abs(slot.moment.hour - 15), slot.moment.hour))
        summaries.append(
            DailySummary(
                day=day,
                temp_min_c=min(temps),
                temp_max_c=max(temps),
                description=description,
                pop_max=max(slot.pop for slot in slots),
                midday_temp_c=midday.temp_c,
            )
        )
    return summaries


def format_forecast(forecast: Forecast) -> str:
    """Прогноз на 5 дней: по суткам, исходный шаг API — 3 часа."""

    place = forecast.city if not forecast.country else f"{forecast.city}, {forecast.country}"
    days = summarize_daily(forecast)
    lines = [
        f"Прогноз на 5 дней: {place}",
        f"Часовой пояс: {format_offset(forecast.timezone_offset_seconds)}",
        "Шаг данных: 3 часа, ниже — сводка по местным суткам.",
    ]
    if not days:
        lines.append("Нет интервалов прогноза.")
        return "\n".join(lines)
    for day in days:
        pop = round(day.pop_max * 100)
        lines.append(
            f"{day.day.strftime('%d.%m')}: {format_number(day.temp_min_c)}…{format_number(day.temp_max_c)} °C, "
            f"днём {format_number(day.midday_temp_c)} °C, {day.description}, "
            f"осадки до {pop}%"
        )
    return "\n".join(lines)


def format_locations(locations: list[GeoLocation]) -> str:
    """Список результатов геокодинга."""

    if not locations:
        return "Ничего не найдено. Уточните название города или координаты."
    lines = ["Найденные места:"]
    for index, location in enumerate(locations, start=1):
        region = f", {location.state}" if location.state else ""
        country = f", {location.country}" if location.country else ""
        lines.append(
            f"{index}. {location.name}{region}{country} — {location.lat:.4f}, {location.lon:.4f}"
        )
    return "\n".join(lines)


def format_air(location: GeoLocation | None, air: AirQuality) -> str:
    """Карточка качества воздуха и расшифровка AQI."""

    if location is None:
        place = f"{air.lat:.4f}, {air.lon:.4f}"
    else:
        place = location.name if not location.country else f"{location.name}, {location.country}"
    label = AQI_LABELS.get(air.aqi, "неизвестно")
    moment = air.moment.astimezone(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    lines = [
        f"Качество воздуха: {place}",
        f"Индекс AQI: {air.aqi} из 5 — {label}",
        "Шкала OpenWeather: 1 — хорошее, 5 — очень плохое.",
        f"Время измерения: {moment}",
        "Компоненты, мкг/м³:",
    ]
    if not air.components:
        lines.append("  нет данных")
    for key, title in COMPONENT_LABELS.items():
        if key in air.components:
            lines.append(f"  {title}: {format_number(air.components[key], 2)}")
    return "\n".join(lines)


def format_comparison(left: CurrentWeather, right: CurrentWeather) -> str:
    """Сравнение текущей погоды двух городов."""

    lines = [
        "Сравнение погоды",
        "",
        _comparison_block(left),
        "",
        _comparison_block(right),
        "",
        _temperature_conclusion(left, right),
    ]
    return "\n".join(lines)


def format_place_and_weather(locations: list[GeoLocation], weather: CurrentWeather) -> str:
    """Обратный геокодинг вместе с текущей погодой по координатам."""

    parts: list[str] = []
    if locations:
        parts.append(format_locations(locations))
        parts.append("")
    parts.append(format_current_weather(weather))
    return "\n".join(parts)


def humanize_error(exc: Exception) -> str:
    """Переводит ошибку сервиса в короткую фразу для пользователя."""

    if isinstance(exc, ValidationError):
        return str(exc)
    if isinstance(exc, WeatherNotFoundError):
        return str(exc) or "Город не найден."
    if isinstance(exc, WeatherAuthError):
        return "Сервис погоды отклонил ключ. Проверьте OPENWEATHER_API_KEY в файле .env."
    if isinstance(exc, WeatherRateLimitError):
        return "Слишком много запросов к OpenWeatherMap. Подождите немного и повторите."
    if isinstance(exc, WeatherServerError):
        return "Сервис OpenWeatherMap временно недоступен. Повторите запрос позже."
    if isinstance(exc, WeatherNetworkError):
        return "Нет соединения с OpenWeatherMap. Проверьте интернет и повторите."
    if isinstance(exc, WeatherResponseError):
        return "OpenWeatherMap вернул непонятный ответ. Повторите запрос позже."
    if isinstance(exc, WeatherAPIError):
        return str(exc) or "Не удалось получить данные о погоде."
    return "Не удалось получить данные о погоде. Попробуйте ещё раз."


def _comparison_block(weather: CurrentWeather) -> str:
    place = weather.city if not weather.country else f"{weather.city}, {weather.country}"
    humidity = "нет данных" if weather.humidity_percent is None else f"{weather.humidity_percent}%"
    return "\n".join(
        [
            place,
            f"  {format_number(weather.temp_c)} °C, {_capitalize(weather.description)}",
            f"  ощущается как {format_optional_number(weather.feels_like_c, '°C')}",
            f"  влажность {humidity}, ветер {format_optional_number(weather.wind_speed_ms, 'м/с')}",
            f"  давление {format_pressure(weather.pressure_hpa)}",
        ]
    )


def _temperature_conclusion(left: CurrentWeather, right: CurrentWeather) -> str:
    delta = left.temp_c - right.temp_c
    if abs(delta) < 0.05:
        return "Температура в городах практически одинаковая."
    if delta > 0:
        return f"В городе {left.city} теплее на {format_number(delta)} °C."
    return f"В городе {right.city} теплее на {format_number(abs(delta))} °C."


def _zone(offset_seconds: int) -> timezone:
    return timezone(timedelta(seconds=offset_seconds))
