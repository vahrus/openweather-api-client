"""Настройка логов без утечки ключей и URL с секретами."""

from __future__ import annotations

import logging
import re

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"(?i)(appid=)[^&\s]+"), r"\1***"),
    (re.compile(r"(?i)(api_key=)[^&\s]+"), r"\1***"),
    (re.compile(r"(?i)(token=)[^&\s]+"), r"\1***"),
    (re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}\b"), "***"),
)


class RedactingFormatter(logging.Formatter):
    """Форматер, который маскирует ключи, если они случайно попали в запись."""

    def format(self, record: logging.LogRecord) -> str:
        return redact_secrets(super().format(record))


def redact_secrets(text: str) -> str:
    """Маскирует типичные секреты в уже собранной строке лога или ошибки."""

    redacted = text
    for pattern, replacement in _SECRET_PATTERNS:
        redacted = pattern.sub(replacement, redacted)
    return redacted


def setup_logging(level: int = logging.INFO) -> None:
    """Включает консольные логи и приглушает библиотеки, которые печатают URL."""

    handler = logging.StreamHandler()
    handler.setFormatter(RedactingFormatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("requests").setLevel(logging.WARNING)
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiohttp").setLevel(logging.WARNING)
