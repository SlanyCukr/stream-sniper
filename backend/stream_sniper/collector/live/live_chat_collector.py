"""One websocket, many rooms, periodic durable flushes."""

import asyncio
import os
from pathlib import Path

from twitchAPI.chat import Chat, ChatEvent
from twitchAPI.oauth import refresh_access_token
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

from ...analytics.rollup_engine import compute_stream_rollup
from ...database.creator_table_gateway import insert_new_creator_db, select_creator_id_db
from ...database.tracked_streamers_table_gateway import select_active_tracked_streamers_db
from ...logging_config import get_logger
from .live_message_sink import LiveMessageSink

logger = get_logger(__name__)


def _read_token(path: str) -> str:
    return Path(path).read_text().strip()


def _write_token(path: str, token: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(token)
    target.chmod(0o600)


class LiveChatCollector:
    def __init__(self, channels=None, flush_interval=None, buffer_size=None):
        configured = channels or os.getenv("LIVE_CHANNELS", "").split(",")
        self._static_channels = {c.strip().lower() for c in configured if c.strip()}
        self.channels: set[str] = set()
        self.tracking_driven = os.getenv("LIVE_TRACKED_CHANNELS", "true").lower() in {"1", "true", "yes"}
        self.flush_interval = float(flush_interval or os.getenv("LIVE_FLUSH_INTERVAL", "5"))
        self.sink = LiveMessageSink(int(buffer_size or os.getenv("LIVE_BUFFER_SIZE", "1000")))
        self.twitch = None
        self.chat = None
        self._running = False
        self._tasks: list[asyncio.Task] = []
        self._streams: dict[str, object] = {}

    async def initialize(self) -> None:
        client_id = os.environ["TWITCH_CLIENT_ID"]
        client_secret = os.environ["TWITCH_CLIENT_SECRET"]
        token_file = os.getenv("TWITCH_BOT_TOKEN_FILE")
        refresh_token = os.getenv("TWITCH_BOT_REFRESH_TOKEN", "")
        if token_file and await asyncio.to_thread(Path(token_file).exists):
            refresh_token = await asyncio.to_thread(_read_token, token_file)
        if not refresh_token:
            raise RuntimeError("TWITCH_BOT_REFRESH_TOKEN or a populated TWITCH_BOT_TOKEN_FILE is required")
        access_token, refreshed = await refresh_access_token(refresh_token, client_id, client_secret)
        if token_file:
            await asyncio.to_thread(_write_token, token_file, refreshed)
        self.twitch = await Twitch(client_id, client_secret)
        if token_file:
            async def persist_refresh(_access_token: str, new_refresh_token: str) -> None:
                await asyncio.to_thread(_write_token, token_file, new_refresh_token)

            self.twitch.user_auth_refresh_callback = persist_refresh
        await self.twitch.set_user_authentication(
            access_token, [AuthScope.CHAT_READ], refresh_token=refreshed,
        )
        self.chat = await Chat(self.twitch)
        self.chat.register_event(ChatEvent.MESSAGE, self._on_message)

    async def start(self) -> None:
        if self.chat is None:
            await self.initialize()
        self._running = True
        self.chat.start()
        await self._sync_channels()
        self._tasks = [
            asyncio.create_task(self._flush_loop()),
            asyncio.create_task(self._status_loop()),
        ]
        logger.info(f"Live chat collector started for {len(self.channels)} channels")
        await asyncio.gather(*self._tasks, return_exceptions=True)

    async def stop(self) -> None:
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        await self.sink.flush()
        if self.chat is not None:
            self.chat.stop()
        if self.twitch is not None:
            await self.twitch.close()

    async def _stream_for(self, channel: str):
        async for stream in self.twitch.get_streams(user_login=[channel], first=1):
            return stream
        return None

    async def _on_message(self, message) -> None:
        channel = message.room.name.lower() if message.room else ""
        stream = self._streams.get(channel)
        if stream is None:
            stream = await self._stream_for(channel)
            if stream is not None:
                self._streams[channel] = stream
        if stream is not None:
            await self.sink.handle(message, stream)

    async def _flush_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self.sink.flush()

    async def _status_loop(self) -> None:
        while self._running:
            await asyncio.sleep(60)
            await self._sync_channels()
            for channel in self.channels:
                active = self.sink.active_session(channel)
                if active is None:
                    continue
                stream = await self._stream_for(channel)
                if stream is None or int(stream.id) != active:
                    stream_id = await self.sink.finalize(channel)
                    self._streams.pop(channel, None)
                    if stream_id is not None:
                        try:
                            await asyncio.to_thread(compute_stream_rollup, stream_id)
                        except Exception:
                            logger.exception(f"Live rollup failed for stream={stream_id}")
                else:
                    self._streams[channel] = stream

    async def _sync_channels(self) -> None:
        desired = set(self._static_channels)
        if self.tracking_driven:
            rows = await asyncio.to_thread(select_active_tracked_streamers_db)
            desired.update(row[2].lower() for row in rows)
        added = desired - self.channels
        removed = self.channels - desired
        if added:
            valid = {channel for channel in added if await self._ensure_creator(channel)}
            desired -= added - valid
            added = valid
            if added:
                await self.chat.join_room(sorted(added))
        if removed:
            await self.chat.leave_room(sorted(removed))
            for channel in removed:
                await self.sink.finalize(channel)
                self._streams.pop(channel, None)
        self.channels = desired

    async def _ensure_creator(self, channel: str) -> bool:
        if await asyncio.to_thread(select_creator_id_db, channel):
            return True
        async for user in self.twitch.get_users(logins=[channel]):
            creator_id = await asyncio.to_thread(
                insert_new_creator_db,
                channel,
                user.display_name,
                user.profile_image_url,
                user.id,
            )
            return creator_id is not None
        logger.warning(f"Cannot join unknown Twitch channel={channel}")
        return False
