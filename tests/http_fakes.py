"""Подмена requests.Session для тестов без сети."""

from __future__ import annotations

import json
from collections.abc import Callable
from typing import Any


class FakeResponse:
    """Минимальный ответ, который читает OpenWeatherClient."""

    def __init__(self, status_code: int, payload: Any, headers: dict[str, str] | None = None) -> None:
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.url = "https://api.openweathermap.org/data/2.5/weather?appid=super-secret-key"
        self.text = payload if isinstance(payload, str) else json.dumps(payload, ensure_ascii=False)

    def json(self) -> Any:
        if isinstance(self._payload, str):
            raise ValueError("invalid json")
        return self._payload


class FakeSession:
    """Запоминает вызовы session.get и отдаёт заранее подготовленный ответ."""

    def __init__(self, responder: FakeResponse | Exception | Callable[[dict[str, Any]], Any]) -> None:
        self._responder = responder
        self.calls: list[dict[str, Any]] = []
        self.headers: dict[str, str] = {}
        self.closed = False

    def get(
        self,
        url: str,
        params: dict[str, Any] | None = None,
        timeout: float | None = None,
        allow_redirects: bool | None = None,
    ) -> FakeResponse:
        call = {
            "url": url,
            "params": dict(params or {}),
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        }
        self.calls.append(call)
        result = self._responder(call) if callable(self._responder) else self._responder
        if isinstance(result, Exception):
            raise result
        return result

    def close(self) -> None:
        self.closed = True
