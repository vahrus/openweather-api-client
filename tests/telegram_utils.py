"""Сборка апдейтов aiogram без сети и без настоящего токена."""

from __future__ import annotations

from datetime import datetime, timezone

from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.base import StorageKey
from aiogram.methods import SendMessage
from aiogram.types import Chat, Location, Message, Update, User

# Короткая заглушка, чтобы конструктор Bot принял строку без сети.
# Это не токен Telegram и не подходит для BotFather.
DUMMY_TOKEN = "1:x"


class UpdateFactory:
    """Нумерует сообщения одного и того же тестового пользователя."""

    def __init__(self, chat_type: str = "private") -> None:
        self.chat_type = chat_type
        self._number = 0

    def message(self, text: str | None = None, location: Location | None = None) -> Update:
        self._number += 1
        return Update(
            update_id=self._number,
            message=Message(
                message_id=self._number,
                date=datetime.now(timezone.utc),
                chat=Chat(id=1, type=self.chat_type),
                from_user=User(id=1, is_bot=False, first_name="Тест"),
                text=text,
                location=location,
            ),
        )


def outgoing_texts(session: object) -> list[str]:
    requests = getattr(session, "requests")
    return [item.text for item in requests if isinstance(item, SendMessage)]


def last_text(session: object) -> str:
    texts = outgoing_texts(session)
    assert texts, "бот ничего не отправил"
    return texts[-1]


async def fsm_snapshot(dispatcher: object, bot_id: int) -> tuple[str | None, dict[str, object]]:
    context = FSMContext(
        storage=dispatcher.storage,  # type: ignore[attr-defined]
        key=StorageKey(bot_id=bot_id, chat_id=1, user_id=1),
    )
    return await context.get_state(), await context.get_data()
