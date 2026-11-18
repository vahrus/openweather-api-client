"""Обработчики команд, кнопок и шагов FSM.

Порядок регистрации в register_handlers обязателен: команды и кнопки меню
объявлены раньше текстовых шагов, поэтому навигация работает из любого состояния.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State
from aiogram.types import Message, ReplyKeyboardMarkup

from services.formatters import (
    format_air,
    format_comparison,
    format_current_weather,
    format_forecast,
    format_place_and_weather,
    humanize_error,
)
from telegram_bot.gateway import AsyncWeatherGateway
from telegram_bot.keyboards import (
    BTN_AIR,
    BTN_COMPARE,
    BTN_FORECAST,
    BTN_GEO,
    BTN_HELP,
    BTN_MENU,
    BTN_WEATHER,
    location_keyboard,
    main_menu_keyboard,
)
from telegram_bot.states import WeatherStates
from telegram_bot.texts import (
    ASK_AIR,
    ASK_COMPARE_FIRST,
    ASK_COMPARE_SECOND,
    ASK_FORECAST,
    ASK_GEO,
    ASK_GEO_GROUP,
    ASK_TEXT,
    ASK_WEATHER,
    CANCELLED,
    FALLBACK,
    HELP,
    LIVE_LOCATION,
    MENU_AGAIN,
    RETRY,
    UNKNOWN_COMMAND,
    WELCOME,
)
from weather_api.exceptions import ValidationError, WeatherAPIError
from weather_api.validation import parse_coordinates, validate_city

logger = logging.getLogger(__name__)

_MESSAGE_LIMIT = 4000


def build_router() -> Router:
    """Собирает новый роутер. У aiogram роутер нельзя подключить к двум диспетчерам."""

    router = Router(name="weather")
    register_handlers(router)
    return router


def register_handlers(router: Router) -> None:
    """Регистрирует обработчики в порядке приоритета."""

    router.message.register(cmd_start, CommandStart())
    router.message.register(cmd_help, Command("help"))
    router.message.register(cmd_cancel, Command("cancel"))
    router.message.register(cmd_weather, Command("weather"))
    router.message.register(cmd_forecast, Command("forecast"))
    router.message.register(cmd_geo, Command("geo"))
    router.message.register(cmd_compare, Command("compare"))
    router.message.register(cmd_air, Command("air"))

    router.message.register(btn_weather, F.text == BTN_WEATHER)
    router.message.register(btn_forecast, F.text == BTN_FORECAST)
    router.message.register(btn_geo, F.text == BTN_GEO)
    router.message.register(btn_compare, F.text == BTN_COMPARE)
    router.message.register(btn_air, F.text == BTN_AIR)
    router.message.register(btn_help, F.text == BTN_HELP)
    router.message.register(btn_menu, F.text == BTN_MENU)
    router.message.register(on_location, F.location)

    router.message.register(weather_city, WeatherStates.waiting_weather_city, F.text)
    router.message.register(forecast_city, WeatherStates.waiting_forecast_city, F.text)
    router.message.register(geo_text, WeatherStates.waiting_geo, F.text)
    router.message.register(compare_first_city, WeatherStates.waiting_compare_first_city, F.text)
    router.message.register(compare_second_city, WeatherStates.waiting_compare_second_city, F.text)
    router.message.register(air_city, WeatherStates.waiting_air_city, F.text)

    router.message.register(weather_city_other, WeatherStates.waiting_weather_city)
    router.message.register(forecast_city_other, WeatherStates.waiting_forecast_city)
    router.message.register(geo_other, WeatherStates.waiting_geo)
    router.message.register(compare_other, WeatherStates.waiting_compare_first_city)
    router.message.register(compare_other, WeatherStates.waiting_compare_second_city)
    router.message.register(air_city_other, WeatherStates.waiting_air_city)
    router.message.register(fallback, StateFilter(None), F.text)


async def cmd_start(message: Message, state: FSMContext) -> None:
    """Сбрасывает сценарий и показывает приветствие с главным меню."""

    await state.clear()
    await message.answer(WELCOME, reply_markup=main_menu_keyboard())


async def cmd_help(message: Message) -> None:
    """Показывает справку и не стирает текущий шаг диалога."""

    await message.answer(HELP, reply_markup=main_menu_keyboard())


async def cmd_cancel(message: Message, state: FSMContext) -> None:
    """Отменяет текущее действие из любого состояния."""

    await state.clear()
    await message.answer(CANCELLED, reply_markup=main_menu_keyboard())


async def cmd_weather(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
    command: CommandObject,
) -> None:
    """Текущая погода. Город можно передать аргументом команды."""

    await _weather_query(message, state, gateway, command.args or "")


async def cmd_forecast(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
    command: CommandObject,
) -> None:
    """Прогноз на 5 дней по городу из аргумента или следующего сообщения."""

    await _forecast_query(message, state, gateway, command.args or "")


async def cmd_geo(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
    command: CommandObject,
) -> None:
    """Погода по координатам из аргумента или запрос геолокации."""

    raw = (command.args or "").strip()
    if not raw:
        await _ask_geo(message, state)
        return
    await state.clear()
    await state.set_state(WeatherStates.waiting_geo)
    try:
        lat, lon = parse_coordinates(raw)
    except ValidationError as exc:
        await _fail(message, exc)
        await message.answer(ASK_GEO, reply_markup=_geo_markup(message))
        return
    await _answer_coordinates(message, state, gateway, lat, lon)


async def cmd_compare(message: Message, state: FSMContext) -> None:
    """Начинает сравнение двух городов."""

    await _begin(message, state, WeatherStates.waiting_compare_first_city, ASK_COMPARE_FIRST)


async def cmd_air(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
    command: CommandObject,
) -> None:
    """Качество воздуха по городу из аргумента или следующего сообщения."""

    await _air_query(message, state, gateway, command.args or "")


async def btn_weather(message: Message, state: FSMContext) -> None:
    """Кнопка «Погода сейчас» из любого состояния."""

    await _begin(message, state, WeatherStates.waiting_weather_city, ASK_WEATHER)


async def btn_forecast(message: Message, state: FSMContext) -> None:
    """Кнопка прогноза из любого состояния."""

    await _begin(message, state, WeatherStates.waiting_forecast_city, ASK_FORECAST)


async def btn_geo(message: Message, state: FSMContext) -> None:
    """Кнопка геолокации из любого состояния."""

    await _ask_geo(message, state)


async def btn_compare(message: Message, state: FSMContext) -> None:
    """Кнопка сравнения городов из любого состояния."""

    await cmd_compare(message, state)


async def btn_air(message: Message, state: FSMContext) -> None:
    """Кнопка качества воздуха из любого состояния."""

    await _begin(message, state, WeatherStates.waiting_air_city, ASK_AIR)


async def btn_help(message: Message) -> None:
    """Кнопка справки. Текущий шаг FSM сохраняется."""

    await cmd_help(message)


async def btn_menu(message: Message, state: FSMContext) -> None:
    """Кнопка «Главное меню» отменяет сценарий."""

    await state.clear()
    await message.answer(MENU_AGAIN, reply_markup=main_menu_keyboard())


async def on_location(message: Message, state: FSMContext, gateway: AsyncWeatherGateway) -> None:
    """Принимает разовую геопозицию и не сохраняет её в данных FSM."""

    location = message.location
    if location is None:
        return
    if location.live_period:
        await message.answer(LIVE_LOCATION)
        return
    if await state.get_state() is None:
        await state.set_state(WeatherStates.waiting_geo)
    await _answer_coordinates(
        message,
        state,
        gateway,
        location.latitude,
        location.longitude,
    )


async def weather_city(message: Message, state: FSMContext, gateway: AsyncWeatherGateway) -> None:
    """Город для текущей погоды."""

    if await _reject_unknown_command(message):
        return
    await _weather_query(message, state, gateway, message.text or "")


async def forecast_city(message: Message, state: FSMContext, gateway: AsyncWeatherGateway) -> None:
    """Город для прогноза."""

    if await _reject_unknown_command(message):
        return
    await _forecast_query(message, state, gateway, message.text or "")


async def geo_text(message: Message, state: FSMContext, gateway: AsyncWeatherGateway) -> None:
    """Координаты текстом, если кнопка геолокации недоступна или неудобна."""

    if await _reject_unknown_command(message):
        return
    try:
        lat, lon = parse_coordinates(message.text or "")
    except ValidationError as exc:
        await _fail(message, exc)
        return
    await _answer_coordinates(message, state, gateway, lat, lon)


async def compare_first_city(message: Message, state: FSMContext) -> None:
    """Запоминает первый город сравнения в данных FSM этого пользователя."""

    if await _reject_unknown_command(message):
        return
    try:
        city = validate_city(message.text or "")
    except ValidationError as exc:
        await _fail(message, exc)
        return
    await state.update_data(compare_first_city=city)
    await state.set_state(WeatherStates.waiting_compare_second_city)
    await message.answer(ASK_COMPARE_SECOND, reply_markup=main_menu_keyboard())


async def compare_second_city(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
) -> None:
    """Сравнивает второй город с уже сохранённым первым."""

    if await _reject_unknown_command(message):
        return
    data = await state.get_data()
    first = data.get("compare_first_city")
    if not isinstance(first, str) or not first:
        await _begin(message, state, WeatherStates.waiting_compare_first_city, ASK_COMPARE_FIRST)
        return
    try:
        left, right = await gateway.compare_cities(first, message.text or "")
    except WeatherAPIError as exc:
        await _fail(message, exc)
        return
    await state.clear()
    await message.answer(_clip(format_comparison(left, right)), reply_markup=main_menu_keyboard())


async def air_city(message: Message, state: FSMContext, gateway: AsyncWeatherGateway) -> None:
    """Город для качества воздуха."""

    if await _reject_unknown_command(message):
        return
    await _air_query(message, state, gateway, message.text or "")


async def weather_city_other(message: Message) -> None:
    """Подсказка, если вместо города прислали не текст."""

    await message.answer(ASK_TEXT)


async def forecast_city_other(message: Message) -> None:
    """Подсказка на нетекстовый ответ в сценарии прогноза."""

    await message.answer(ASK_TEXT)


async def geo_other(message: Message) -> None:
    """Подсказка, если в сценарии геолокации прислали не точку и не координаты."""

    await message.answer(ASK_GEO, reply_markup=_geo_markup(message))


async def compare_other(message: Message) -> None:
    """Подсказка на нетекстовый ответ в сравнении городов."""

    await message.answer(ASK_TEXT)


async def air_city_other(message: Message) -> None:
    """Подсказка на нетекстовый ответ в сценарии качества воздуха."""

    await message.answer(ASK_TEXT)


async def fallback(message: Message) -> None:
    """Ответ, когда нет активного сценария и текст не похож на команду."""

    await message.answer(FALLBACK, reply_markup=main_menu_keyboard())


async def _weather_query(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
    raw_city: str,
) -> None:
    city = raw_city.strip()
    if not city:
        await _begin(message, state, WeatherStates.waiting_weather_city, ASK_WEATHER)
        return
    try:
        weather = await gateway.current_by_city(city)
    except WeatherAPIError as exc:
        await _fail(message, exc)
        await state.clear()
        await state.set_state(WeatherStates.waiting_weather_city)
        return
    await state.clear()
    await message.answer(_clip(format_current_weather(weather)), reply_markup=main_menu_keyboard())


async def _forecast_query(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
    raw_city: str,
) -> None:
    city = raw_city.strip()
    if not city:
        await _begin(message, state, WeatherStates.waiting_forecast_city, ASK_FORECAST)
        return
    try:
        forecast = await gateway.forecast_by_city(city)
    except WeatherAPIError as exc:
        await _fail(message, exc)
        await state.clear()
        await state.set_state(WeatherStates.waiting_forecast_city)
        return
    await state.clear()
    await message.answer(_clip(format_forecast(forecast)), reply_markup=main_menu_keyboard())


async def _air_query(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
    raw_city: str,
) -> None:
    city = raw_city.strip()
    if not city:
        await _begin(message, state, WeatherStates.waiting_air_city, ASK_AIR)
        return
    try:
        location, air = await gateway.air_by_city(city)
    except WeatherAPIError as exc:
        await _fail(message, exc)
        await state.clear()
        await state.set_state(WeatherStates.waiting_air_city)
        return
    await state.clear()
    await message.answer(_clip(format_air(location, air)), reply_markup=main_menu_keyboard())


async def _answer_coordinates(
    message: Message,
    state: FSMContext,
    gateway: AsyncWeatherGateway,
    lat: float,
    lon: float,
) -> None:
    try:
        places, weather = await gateway.place_and_weather(lat, lon)
    except WeatherAPIError as exc:
        await _fail(message, exc)
        if await state.get_state() is None:
            await state.set_state(WeatherStates.waiting_geo)
        return
    await state.clear()
    await message.answer(
        _clip(format_place_and_weather(places, weather)),
        reply_markup=main_menu_keyboard(),
    )


async def _ask_geo(message: Message, state: FSMContext) -> None:
    prompt = ASK_GEO if _is_private(message) else f"{ASK_GEO_GROUP}\n{ASK_GEO}"
    await state.clear()
    await state.set_state(WeatherStates.waiting_geo)
    await message.answer(prompt, reply_markup=_geo_markup(message))


async def _begin(message: Message, state: FSMContext, new_state: State, prompt: str) -> None:
    await state.clear()
    await state.set_state(new_state)
    await message.answer(prompt, reply_markup=main_menu_keyboard())


async def _fail(message: Message, exc: WeatherAPIError) -> None:
    logger.warning("Ошибка погодного сценария: %s", exc.__class__.__name__)
    await message.answer(f"{humanize_error(exc)}\n\n{RETRY}")


async def _reject_unknown_command(message: Message) -> bool:
    """Отвечает на незарегистрированную команду и не отправляет её в API как город."""

    if not (message.text or "").startswith("/"):
        return False
    await message.answer(UNKNOWN_COMMAND)
    return True


def _is_private(message: Message) -> bool:
    return message.chat.type == "private"


def _geo_markup(message: Message) -> ReplyKeyboardMarkup:
    return location_keyboard(private=_is_private(message))


def _clip(text: str) -> str:
    if len(text) <= _MESSAGE_LIMIT:
        return text
    return text[: _MESSAGE_LIMIT - 1] + "…"
