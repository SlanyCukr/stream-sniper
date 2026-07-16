"""Build typed database rows from normalized Twitch chat batches."""

from dataclasses import dataclass
from datetime import datetime

from .chat_parser import ParsedChatBatch

MessageInsertRow = tuple[
    int,
    int | None,
    int,
    int,
    datetime,
    bool | None,
    str | None,
    int | None,
    str | None,
]


@dataclass(frozen=True)
class MessagePersistenceBatch:
    rows: tuple[MessageInsertRow, ...]
    message_count: int
    emotes: tuple[tuple[str, str | None], ...]


def _tagged_user_id(message: str, chatter_ids: dict[str, int]) -> int | None:
    if "@" not in message:
        return None
    mention = message.lower().split("@", 1)[1].split(" ", 1)[0]
    return chatter_ids.get(mention)


def build_message_rows(
    batch: ParsedChatBatch,
    stream_id: int,
    chatter_ids: dict[str, int],
    message_ids: dict[str, int],
) -> MessagePersistenceBatch:
    """Resolve a parsed batch against explicit ID maps and return insert rows."""
    rows = tuple(
        (
            chatter_ids[line.chatter_nick],
            _tagged_user_id(line.message, chatter_ids),
            stream_id,
            message_ids[line.message],
            line.timestamp,
            line.is_subscriber,
            line.badges,
            line.emote_count,
            line.source_message_id,
        )
        for line in batch.lines
    )
    return MessagePersistenceBatch(rows=rows, message_count=len(rows), emotes=batch.emotes)
