"""Проверка городов и координат до обращения к API."""

from __future__ import annotations

import math
import re

from weather_api.exceptions import ValidationError

_MAX_CITY_LENGTH = 80
_CITY_RE = re.compile(r"^(?=.*[\w])[\w][\w .,'’-]{0,79}$", re.UNICODE)
_COORD_START_RE = re.compile(r"^[+-]?\d")


def validate_city(value: str) -> str:
    """Возвращает очищенное название города либо возбуждает ValidationError.

    Допустимы буквы (включая кириллицу), цифры, пробел, дефис, апостроф,
    точка и запятая — чтобы можно было уточнить страну: «Москва, RU».
    """

    raw = (value or "").strip()
    if not raw:
        raise ValidationError("Введите название города.")
    if any(ord(char) < 32 for char in raw):
        raise ValidationError("Название города содержит недопустимые символы.")
    city = " ".join(raw.split())
    if len(city) > _MAX_CITY_LENGTH:
        raise ValidationError("Название города слишком длинное.")
    if not _CITY_RE.fullmatch(city):
        raise ValidationError(
            "Название города может содержать буквы, пробел, дефис и запятую."
        )
    return city


def looks_like_coordinates(value: str) -> bool:
    """Отличает ввод координат от названия города."""

    raw = (value or "").strip()
    if not raw or _COORD_START_RE.match(raw) is None:
        return False
    if any(separator in raw for separator in (",", ";")):
        return True
    return len(raw.split()) == 2


def parse_coordinates(value: str) -> tuple[float, float]:
    """Разбирает строку вида «55.7558, 37.6173» в пару (широта, долгота)."""

    raw = (value or "").strip()
    if not raw:
        raise ValidationError("Введите координаты в формате 55.7558, 37.6173.")
    if "," in raw:
        parts = [part.strip() for part in raw.split(",")]
    elif ";" in raw:
        parts = [part.strip() for part in raw.split(";")]
    else:
        parts = raw.split()
    if len(parts) != 2:
        raise ValidationError("Введите широту и долготу в формате 55.7558, 37.6173.")
    try:
        lat = float(parts[0])
        lon = float(parts[1])
    except ValueError as exc:
        raise ValidationError(
            "Координаты должны быть числами, например 55.7558, 37.6173."
        ) from exc
    validate_coordinates(lat, lon)
    return lat, lon


def validate_coordinates(lat: float, lon: float) -> None:
    """Проверяет диапазоны широты и долготы."""

    if not math.isfinite(lat) or not math.isfinite(lon):
        raise ValidationError("Координаты должны быть конечными числами.")
    if not -90 <= lat <= 90:
        raise ValidationError("Широта должна быть в диапазоне от -90 до 90.")
    if not -180 <= lon <= 180:
        raise ValidationError("Долгота должна быть в диапазоне от -180 до 180.")


def validate_limit(limit: int) -> int:
    """Ограничивает число результатов геокодинга разумным диапазоном."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 5:
        raise ValidationError("Число результатов геокодинга должно быть от 1 до 5.")
    return limit
