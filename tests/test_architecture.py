"""Границы слоёв, .gitignore и отсутствие секретов в дереве проекта."""

from __future__ import annotations

import fnmatch
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOKEN_RE = re.compile(r"\b\d{6,}:[A-Za-z0-9_-]{20,}")
SKIP_PARTS = {".venv", "tests", "__pycache__", ".pytest_cache"}


def _project_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.name == ".env" or any(part in SKIP_PARTS for part in path.parts):
            continue
        files.append(path)
    return files


def test_api_and_cli_do_not_import_aiogram() -> None:
    code = (
        "import cli, services.weather_service, weather_api.client, sys; "
        "raise SystemExit(1 if any(name == 'aiogram' or name.startswith('aiogram.') for name in sys.modules) else 0)"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_telegram_handlers_do_not_call_requests_directly() -> None:
    handlers = (ROOT / "telegram_bot" / "handlers.py").read_text(encoding="utf-8")
    gateway = (ROOT / "telegram_bot" / "gateway.py").read_text(encoding="utf-8")
    client = (ROOT / "weather_api" / "client.py").read_text(encoding="utf-8")

    assert "import requests" not in handlers
    assert "asyncio.to_thread" not in handlers
    assert "asyncio.to_thread" in gateway
    assert "aiogram" not in client
    assert "global " not in handlers


def _gitignore_rules(text: str) -> list[str]:
    """Возвращает непустые правила, без комментариев."""

    rules: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        rules.append(line)
    return rules


def _pattern_matches(pattern: str, relative: str, *, is_dir: bool) -> bool:
    """Проверяет одно правило gitignore для пути внутри проекта."""

    directory_only = pattern.endswith("/")
    if directory_only and not is_dir:
        return False
    anchored = pattern.startswith("/")
    body = pattern.lstrip("/").rstrip("/")
    if not body:
        return False
    candidate = relative.rstrip("/")
    target = candidate if anchored or "/" in body else Path(candidate).name
    return fnmatch.fnmatchcase(target, body)


def _ignored_by_rules(rules: list[str], relative: str, *, is_dir: bool = False) -> bool:
    """Повторяет порядок gitignore: срабатывает последнее подходящее правило."""

    ignored = False
    for rule in rules:
        negated = rule.startswith("!")
        pattern = rule[1:] if negated else rule
        if _pattern_matches(pattern, relative, is_dir=is_dir):
            ignored = not negated
    return ignored


def _project_git_root() -> Path | None:
    """Корень Git этого проекта. Родительский репозиторий не считается."""

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    top = Path(result.stdout.strip()).resolve()
    return top if top == ROOT else None


def _git_check_ignore(relative: str) -> bool:
    """True, если путь игнорируется. Содержимое файлов не читается."""

    result = subprocess.run(
        ["git", "check-ignore", "-q", "--", relative],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise AssertionError(f"git check-ignore не смог проверить {relative}: код {result.returncode}")


def test_gitignore_covers_env_and_venv() -> None:
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    rules = _gitignore_rules(text)
    assert any(rule in {".env", "/.env"} for rule in rules)
    assert any(rule in {".venv/", "/.venv/"} for rule in rules)
    assert _ignored_by_rules(rules, ".env")
    assert _ignored_by_rules(rules, ".venv", is_dir=True)
    assert (ROOT / ".env.example").is_file()
    assert not _ignored_by_rules(rules, ".env.example")

    if _project_git_root() is None:
        return
    assert _git_check_ignore(".env")
    assert _git_check_ignore(".venv")
    assert not _git_check_ignore(".env.example")


def test_repository_files_do_not_contain_live_secrets() -> None:
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "replace_with_your_openweather_key" in example
    assert "replace_with_your_telegram_bot_token" in example
    assert TOKEN_RE.search(example) is None

    for path in _project_files():
        if path.suffix not in {".py", ".md", ".txt", ".toml", ".example"} and path.name != ".env.example":
            continue
        text = path.read_text(encoding="utf-8")
        assert "super-secret-key" not in text
        assert TOKEN_RE.search(text) is None, path
