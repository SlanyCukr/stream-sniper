"""Build typed database rows from normalized Twitch chat batches."""

from dataclasses import dataclass

from ...database.gateways.chat.message_table_gateway import MessageInsertRow
from ..mention import mention_token
from .chat_parser import ParsedChatBatch


@dataclass(frozen=True)
class MessagePersistenceBatch:
    rows: tuple[MessageInsertRow, ...]
    message_count: int
    emotes: tuple[tuple[str, str | None], ...]


def _tagged_user_id(message: str, chatter_ids: dict[str, int]) -> int | None:
    token = mention_token(message)
    return chatter_ids.get(token) if token is not None else None


def collect_mention_nicks(batch: ParsedChatBatch) -> list[str]:
    """Lowercased @mention tokens across the batch, so the chatter-id lookup can
    stay batch-scoped and still resolve mentions of chatters seen in past streams."""
    return sorted({token for line in batch.lines if (token := mention_token(line.message))})


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
