"""Bounded, asynchronous sink from Twitch IRC events to canonical message rows."""

import asyncio
from datetime import UTC, datetime

from ...database.chatter_table_gateway import insert_new_chatter_db
from ...database.live_chat_table_gateway import (
    bulk_insert_live_messages_db,
    ensure_live_stream_db,
    finalize_live_stream_db,
)
from ...database.message_text_table_gateway import find_or_insert_message_text_id_db
from ...logging_config import get_logger

logger = get_logger(__name__)


def _emote_count(raw) -> int:
    """Count IRC emote ranges from ``id:start-end,start-end/id:start-end``."""
    if not raw:
        return 0
    return sum(
        len(group.split(":", 1)[1].split(","))
        for group in str(raw).split("/")
        if ":" in group and group.split(":", 1)[1]
    )


def _badge_text(raw) -> str | None:
    """Match the canonical ``name/version`` text used by VOD ingestion."""
    if not raw:
        return None
    if isinstance(raw, dict):
        pairs = (
            f"{name}/{version if version is not None else 0}"
            for name, version in sorted(raw.items())
            if name
        )
        return ",".join(pairs) or None
    return str(raw)


class LiveMessageSink:
    def __init__(self, buffer_size: int = 1000):
        self.buffer_size = max(10, buffer_size)
        self._items: list[tuple] = []
        self._streams: dict[str, tuple[int, int]] = {}
        self._chatters: dict[str, int] = {}
        self._texts: dict[str, int] = {}
        self._flush_lock = asyncio.Lock()

    async def set_stream(self, channel: str, stream) -> int | None:
        session_id = int(stream.id)
        current = self._streams.get(channel)
        if current and current[0] == session_id:
            return current[1]
        stream_id = await asyncio.to_thread(
            ensure_live_stream_db,
            channel,
            session_id,
            stream.started_at,
            stream.title,
            stream.thumbnail_url,
        )
        if stream_id is not None:
            self._streams[channel] = (session_id, stream_id)
        return stream_id

    async def handle(self, message, stream) -> bool:
        channel = message.room.name.lower() if message.room else None
        if not channel or not message.id:
            return False
        stream_id = await self.set_stream(channel, stream)
        if stream_id is None:
            logger.warning(f"Ignoring live message for unknown creator channel={channel}")
            return False

        nick = message.user.name.lower()
        chatter_id = self._chatters.get(nick)
        if chatter_id is None:
            chatter_id = await asyncio.to_thread(insert_new_chatter_db, nick)
            self._chatters[nick] = chatter_id

        text = message.text
        text_id = self._texts.get(text)
        if text_id is None:
            text_id = await asyncio.to_thread(find_or_insert_message_text_id_db, text)
            self._texts[text] = text_id

        tagged_id = None
        if "@" in text:
            tagged = text.lower().split("@", 1)[1].split(" ", 1)[0].rstrip(".,:;!?")
            tagged_id = self._chatters.get(tagged)
        badges = _badge_text(message.user.badges)
        emote_count = _emote_count(message.emotes)
        sent_at = datetime.fromtimestamp(message.sent_timestamp / 1000, UTC)
        self._items.append(
            (
                chatter_id, tagged_id, stream_id, text_id, sent_at,
                message.user.subscriber, badges, emote_count, message.id,
            )
        )
        if len(self._items) >= self.buffer_size:
            await self.flush()
        return True

    async def flush(self) -> None:
        async with self._flush_lock:
            if not self._items:
                return
            batch, self._items = self._items, []
            try:
                await asyncio.to_thread(bulk_insert_live_messages_db, batch)
            except Exception:
                self._items = batch + self._items
                logger.exception(f"Live message flush failed; retained {len(batch)} rows")

    async def finalize(self, channel: str, ended_at=None) -> int | None:
        await self.flush()
        current = self._streams.pop(channel, None)
        if current is None:
            return None
        await asyncio.to_thread(finalize_live_stream_db, current[1], ended_at)
        return current[1]

    def active_session(self, channel: str) -> int | None:
        current = self._streams.get(channel)
        return current[0] if current else None
