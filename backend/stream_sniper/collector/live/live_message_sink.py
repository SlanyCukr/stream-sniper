"""Bounded, asynchronous sink from Twitch IRC events to canonical message rows."""

import asyncio
from collections.abc import Callable, Mapping
from datetime import UTC, datetime
from typing import Any

from ...database.core.connection_pool import (
    DatabaseConnectionPool,
    enter_pool_scope,
    exit_pool_scope,
    peek_active_pool,
)
from ...database.gateways.chat.chatter_table_gateway import find_or_insert_chatter_id_db
from ...database.gateways.chat.live_chat_table_gateway import (
    LiveMessageRow,
    bulk_insert_live_messages_db,
    ensure_live_stream_db,
    finalize_live_stream_db,
)
from ...database.gateways.chat.message_text_table_gateway import find_or_insert_message_text_id_db
from ...logging_config import get_logger
from .contracts import ChatMessage, LiveStream

logger = get_logger(__name__)
DEFAULT_BUFFER_SIZE = 1_000
MILLISECONDS_PER_SECOND = 1_000


class LiveMessageFlushError(RuntimeError):
    """A retained live-message batch could not be persisted."""

    def __init__(self, retained_rows: int):
        self.retained_rows = retained_rows
        super().__init__(f"Failed to persist {retained_rows} live message rows; batch retained")


def _emote_count(raw: object | None) -> int:
    """Count IRC emote ranges from ``id:start-end,start-end/id:start-end``."""
    if not raw:
        return 0
    return sum(
        len(group.split(":", 1)[1].split(","))
        for group in str(raw).split("/")
        if ":" in group and group.split(":", 1)[1]
    )


def _badge_text(raw: object | None) -> str | None:
    """Match the canonical ``name/version`` text used by VOD ingestion."""
    if not raw:
        return None
    if isinstance(raw, Mapping):
        pairs = (f"{name}/{version if version is not None else 0}" for name, version in sorted(raw.items()) if name)
        return ",".join(pairs) or None
    return str(raw)


class LiveMessageSink:
    def __init__(self, buffer_size: int = DEFAULT_BUFFER_SIZE):
        self.buffer_size = max(10, buffer_size)
        self._items: list[LiveMessageRow] = []
        self._streams: dict[str, tuple[int, int]] = {}
        self._chatters: dict[str, int] = {}
        self._texts: dict[str, int] = {}
        self._flush_lock = asyncio.Lock()
        self._channel_locks: dict[str, asyncio.Lock] = {}
        self._finalized_sessions: dict[str, int] = {}
        # twitchAPI's chat client invokes message callbacks on its own thread, whose
        # context never saw the service entrypoint's pool binding (ContextVars do not
        # cross thread boundaries). Capture the pool here — the sink is constructed
        # inside the service's database runtime — and re-bind it around every
        # worker-thread gateway call. None (unit tests) falls back to the ambient
        # context so gateway monkeypatching keeps working unchanged.
        self._pool: DatabaseConnectionPool | None = peek_active_pool()

    def _call_with_pool(self, gateway: Callable[..., Any], /, *args: Any) -> Any:
        """Run a gateway call with the captured pool bound in the worker thread."""
        if self._pool is None:
            return gateway(*args)
        token = enter_pool_scope(self._pool)
        try:
            return gateway(*args)
        finally:
            exit_pool_scope(token)

    def _channel_lock(self, channel: str) -> asyncio.Lock:
        return self._channel_locks.setdefault(channel, asyncio.Lock())

    async def ensure_stream(self, channel: str, stream: LiveStream) -> int | None:
        channel = channel.lower()
        async with self._channel_lock(channel):
            return await self._ensure_stream(channel, stream)

    async def _ensure_stream(self, channel: str, stream: LiveStream) -> int | None:
        twitch_stream_session_id = int(stream.id)
        if self._finalized_sessions.get(channel) == twitch_stream_session_id:
            return None
        current = self._streams.get(channel)
        if current and current[0] == twitch_stream_session_id:
            return current[1]
        stream_id_raw = await asyncio.to_thread(
            self._call_with_pool,
            ensure_live_stream_db,
            channel,
            twitch_stream_session_id,
            stream.started_at,
            stream.title,
            stream.thumbnail_url,
        )
        stream_id = int(stream_id_raw) if stream_id_raw is not None else None
        if stream_id is not None:
            self._streams[channel] = (twitch_stream_session_id, stream_id)
            self._finalized_sessions.pop(channel, None)
        return stream_id

    async def _resolve_chatter_id(self, nick: str) -> int:
        chatter_id = self._chatters.get(nick)
        if chatter_id is None:
            chatter_id = await asyncio.to_thread(self._call_with_pool, find_or_insert_chatter_id_db, nick)
            if chatter_id is None:
                raise RuntimeError(f"Chatter persistence returned no ID for {nick}")
            self._chatters[nick] = chatter_id
        return chatter_id

    async def _resolve_text_id(self, text: str) -> int:
        text_id = self._texts.get(text)
        if text_id is None:
            text_id = await asyncio.to_thread(self._call_with_pool, find_or_insert_message_text_id_db, text)
            if text_id is None:
                raise RuntimeError("Message-text persistence returned no ID")
            self._texts[text] = text_id
        return text_id

    def _tagged_chatter_id(self, text: str) -> int | None:
        if "@" not in text:
            return None
        tagged = text.lower().split("@", 1)[1].split(" ", 1)[0].rstrip(".,:;!?")
        return self._chatters.get(tagged)

    def _message_row(
        self,
        message: ChatMessage,
        *,
        chatter_id: int,
        stream_id: int,
        text_id: int,
    ) -> LiveMessageRow:
        source_message_id = message.id
        if source_message_id is None:
            raise ValueError("Live message row requires a Twitch source message ID")
        return (
            chatter_id,
            self._tagged_chatter_id(message.text),
            stream_id,
            text_id,
            datetime.fromtimestamp(message.sent_timestamp / MILLISECONDS_PER_SECOND, UTC),
            message.user.subscriber,
            _badge_text(message.user.badges),
            _emote_count(message.emotes),
            source_message_id,
        )

    async def ingest_message(self, message: ChatMessage, stream: LiveStream) -> bool:
        channel = message.room.name.lower() if message.room else None
        if not channel or not message.id:
            return False
        twitch_stream_session_id = int(stream.id)
        async with self._channel_lock(channel):
            if self._finalized_sessions.get(channel) == twitch_stream_session_id:
                return False
            stream_id = await self._ensure_stream(channel, stream)
            if stream_id is None:
                logger.warning(f"Ignoring live message for unknown creator channel={channel}")
                return False

            chatter_id = await self._resolve_chatter_id(message.user.name.lower())
            text_id = await self._resolve_text_id(message.text)
            self._items.append(
                self._message_row(
                    message,
                    chatter_id=chatter_id,
                    stream_id=stream_id,
                    text_id=text_id,
                )
            )
            if len(self._items) >= self.buffer_size:
                await self.flush()
            return True

    async def flush(self) -> int:
        async with self._flush_lock:
            if not self._items:
                return 0
            batch, self._items = self._items, []
            try:
                await asyncio.to_thread(self._call_with_pool, bulk_insert_live_messages_db, batch)
            except Exception as error:
                self._items = batch + self._items
                logger.exception(f"Live message flush failed; retained {len(batch)} rows")
                raise LiveMessageFlushError(len(batch)) from error
            return len(batch)

    async def finalize(self, channel: str, ended_at: datetime | None = None) -> int | None:
        channel = channel.lower()
        async with self._channel_lock(channel):
            current = self._streams.get(channel)
            if current is None:
                return None
            await self.flush()
            await asyncio.to_thread(self._call_with_pool, finalize_live_stream_db, current[1], ended_at)
            self._streams.pop(channel, None)
            self._finalized_sessions[channel] = current[0]
            return current[1]

    def active_twitch_session_id(self, channel: str) -> int | None:
        current = self._streams.get(channel)
        return current[0] if current else None
