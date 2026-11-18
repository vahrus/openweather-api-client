"""Интерактивное меню CLI без настоящих запросов."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from cli import main, run_menu
from tests.samples import moscow_weather
from weather_api.exceptions import WeatherNotFoundError


def _input(answers: list[str]):
    stream: Iterator[str] = iter(answers)

    def read(_prompt: str) -> str:
        return next(stream)

    return read


def test_menu_lists_items_and_exits(capsys: pytest.CaptureFixture[str]) -> None:
    run_menu(service=None, input_func=_input(["0"]))  # type: ignore[arg-type]

    output = capsys.readouterr().out
    assert "1 — Погода сейчас" in output
    assert "2 — Прогноз на 5 дней" in output
    assert "3 — Погода по координатам" in output
    assert "4 — Геокодинг" in output
    assert "5 — Качество воздуха" in output
    assert "6 — Сравнение городов" in output
    assert "0 — Выход" in output
    assert output.strip().endswith("Выход.")


def test_unknown_menu_item_is_rejected(capsys: pytest.CaptureFixture[str]) -> None:
    run_menu(service=None, input_func=_input(["9", "0"]))  # type: ignore[arg-type]

    assert "Выберите пункт меню: 0–6." in capsys.readouterr().out


def test_current_weather_item_uses_service(capsys: pytest.CaptureFixture[str]) -> None:
    class Stub:
        def current_by_city(self, city: str):
            self.city = city
            return moscow_weather()

    stub = Stub()
    run_menu(stub, input_func=_input(["1", "Москва", "0"]))  # type: ignore[arg-type]

    output = capsys.readouterr().out
    assert stub.city == "Москва"
    assert "Погода: Москва, RU" in output
    assert "768 мм рт. ст." in output


def test_service_error_is_printed_and_menu_continues(capsys: pytest.CaptureFixture[str]) -> None:
    class Stub:
        def current_by_city(self, city: str):
            raise WeatherNotFoundError("Город не найден.")

    run_menu(Stub(), input_func=_input(["1", "Атлантида", "0"]))  # type: ignore[arg-type]

    output = capsys.readouterr().out
    assert "Город не найден." in output
    assert output.strip().endswith("Выход.")


def test_main_requires_api_key(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
    monkeypatch.setattr("cli.load_dotenv", lambda *args, **kwargs: False)
    monkeypatch.setattr("cli.setup_logging", lambda: None)

    assert main() == 1
    assert "OPENWEATHER_API_KEY" in capsys.readouterr().out
