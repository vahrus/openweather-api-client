"""Консольное меню клиента OpenWeatherMap.

Запуск из корня проекта: python cli.py
"""

from __future__ import annotations

import os
from collections.abc import Callable
from typing import TextIO

from dotenv import load_dotenv

from services.formatters import (
    format_air,
    format_comparison,
    format_current_weather,
    format_forecast,
    format_locations,
    format_place_and_weather,
    humanize_error,
)
from services.weather_service import WeatherService
from weather_api.client import OpenWeatherClient
from weather_api.exceptions import WeatherAPIError
from weather_api.logging_utils import setup_logging
from weather_api.validation import parse_coordinates

MENU = """
OpenWeather — учебный клиент
1 — Погода сейчас
2 — Прогноз на 5 дней
3 — Погода по координатам
4 — Геокодинг
5 — Качество воздуха
6 — Сравнение городов
0 — Выход
""".strip()


def run_menu(
    service: WeatherService,
    input_func: Callable[[str], str] = input,
    output_func: Callable[[str], None] = print,
) -> None:
    """Крутит интерактивное меню, пока пользователь не выберет выход."""

    actions = {
        "1": lambda: _current(service, input_func, output_func),
        "2": lambda: _forecast(service, input_func, output_func),
        "3": lambda: _by_coordinates(service, input_func, output_func),
        "4": lambda: _geocode(service, input_func, output_func),
        "5": lambda: _air(service, input_func, output_func),
        "6": lambda: _compare(service, input_func, output_func),
    }
    while True:
        output_func(MENU)
        try:
            choice = input_func("Выберите пункт: ").strip()
        except EOFError:
            output_func("Выход.")
            return
        if choice == "0":
            output_func("Выход.")
            return
        action = actions.get(choice)
        if action is None:
            output_func("Выберите пункт меню: 0–6.")
            continue
        try:
            action()
        except WeatherAPIError as exc:
            output_func(humanize_error(exc))
        except EOFError:
            output_func("Выход.")
            return


def main(argv: list[str] | None = None, env_file: str | None = None, stdout: TextIO | None = None) -> int:
    """Загружает ключ из окружения и открывает меню. Аргументы оставлены для совместимости."""

    del argv, stdout
    load_dotenv(env_file)
    setup_logging()
    api_key = os.getenv("OPENWEATHER_API_KEY", "").strip()
    if not api_key:
        print("Не задан OPENWEATHER_API_KEY. Скопируйте .env.example в .env и укажите ключ.")
        return 1
    client = OpenWeatherClient(api_key)
    try:
        run_menu(WeatherService(client))
    except KeyboardInterrupt:
        print("\nВыход.")
    finally:
        client.close()
    return 0


def _ask(input_func: Callable[[str], str], prompt: str) -> str:
    return input_func(prompt).strip()


def _current(service: WeatherService, input_func: Callable[[str], str], output_func: Callable[[str], None]) -> None:
    city = _ask(input_func, "Введите название города: ")
    output_func(format_current_weather(service.current_by_city(city)))


def _forecast(service: WeatherService, input_func: Callable[[str], str], output_func: Callable[[str], None]) -> None:
    city = _ask(input_func, "Введите название города: ")
    output_func(format_forecast(service.forecast_by_city(city)))


def _by_coordinates(
    service: WeatherService, input_func: Callable[[str], str], output_func: Callable[[str], None]
) -> None:
    raw = _ask(input_func, "Введите широту и долготу (55.7558, 37.6173): ")
    lat, lon = parse_coordinates(raw)
    places, weather = service.place_and_weather(lat, lon)
    output_func(format_place_and_weather(places, weather))


def _geocode(service: WeatherService, input_func: Callable[[str], str], output_func: Callable[[str], None]) -> None:
    query = _ask(input_func, "Введите город или координаты (55.7558, 37.6173): ")
    output_func(format_locations(service.geocode(query)))


def _air(service: WeatherService, input_func: Callable[[str], str], output_func: Callable[[str], None]) -> None:
    city = _ask(input_func, "Введите название города: ")
    location, air = service.air_by_city(city)
    output_func(format_air(location, air))


def _compare(service: WeatherService, input_func: Callable[[str], str], output_func: Callable[[str], None]) -> None:
    first = _ask(input_func, "Первый город: ")
    second = _ask(input_func, "Второй город: ")
    left, right = service.compare_cities(first, second)
    output_func(format_comparison(left, right))


if __name__ == "__main__":
    raise SystemExit(main())
