"""One websocket, many rooms, periodic durable flushes."""

import asyncio
import os
from pathlib import Path
from typing import cast

from twitchAPI.chat import Chat, ChatEvent
from twitchAPI.oauth import refresh_access_token
from twitchAPI.twitch import Twitch
from twitchAPI.type import AuthScope

from ...analytics.rollups.rollup_engine import compute_stream_rollup
from ...database.gateways.chat.live_chat_table_gateway import sweep_stale_live_sessions_db
from ...database.gateways.identity.creator_table_gateway import find_or_insert_creator_id_db, select_creator_id_db
from ...database.gateways.tracking.tracked_streamers_table_gateway import select_active_tracked_streamers_db
from ...logging_config import get_logger
from ..twitch_api import TwitchCredentials
from .contracts import ChatMessage, LiveStream
from .live_message_sink import LiveMessageFlushError, LiveMessageSink
from .secure_files import write_private_text

logger = get_logger(__name__)
_MAX_ROLLUP_ATTEMPTS = 5

# A live-captured row with no chat message AND no viewer sample for this long is a zombie
# (its session died while the service was down — the reconcile loop only finalizes channels
# in the sink's in-memory map, so restarts leak rows). Conservative on purpose: no live
# stream in the tracked scene is silent on both signals for 12 hours, and the viewer-sample
# guard alone keeps any genuinely-live tracked stream open.
_STALE_SESSION_HOURS = 12
# The sweep runs at startup (clearing leaks from the last downtime) and then hourly — the
# status loop ticks every 60s, so re-sweep every 60 ticks.
_SWEEP_EVERY_TICKS = 60


def _read_token(path: str) -> str:
    return Path(path).read_text().strip()


def _write_token(path: str, token: str) -> None:
    write_private_text(path, token)


class LiveChatCollector:
    def __init__(
        self,
        channels: list[str] | None = None,
        flush_interval: float | None = None,
        buffer_size: int | None = None,
    ) -> None:
        configured = channels if channels is not None else os.getenv("LIVE_CHANNELS", "").split(",")
        self._static_channels = {c.strip().lower() for c in configured if c.strip()}
        self.channels: set[str] = set()
        self.tracking_driven = os.getenv("LIVE_TRACKED_CHANNELS", "true").lower() in {"1", "true", "yes"}
        self.flush_interval = (
            flush_interval if flush_interval is not None else float(os.getenv("LIVE_FLUSH_INTERVAL", "5"))
        )
        resolved_buffer_size = buffer_size if buffer_size is not None else int(os.getenv("LIVE_BUFFER_SIZE", "1000"))
        self.sink = LiveMessageSink(resolved_buffer_size)
        self.twitch: Twitch | None = None
        self.chat: Chat | None = None
        self._running = False
        self._tasks: list[asyncio.Task[None]] = []
        self._streams: dict[str, LiveStream] = {}
        self.rollup_failures: dict[int, str] = {}
        self._pending_rollups: dict[int, int] = {}
        self._resources_closed = False
        self._flush_complete = False
        self._stop_lock = asyncio.Lock()

    async def initialize(self) -> None:
        credentials = TwitchCredentials.from_env()
        client_id = credentials.client_id
        client_secret = credentials.client_secret
        token_file = os.getenv("TWITCH_BOT_TOKEN_FILE")
        refresh_token = os.getenv("TWITCH_BOT_REFRESH_TOKEN", "")
        token_path = Path(token_file) if token_file else None
        if token_path is not None and await asyncio.to_thread(token_path.exists):
            refresh_token = await asyncio.to_thread(_read_token, str(token_path))
        if not refresh_token:
            raise RuntimeError("TWITCH_BOT_REFRESH_TOKEN or a populated TWITCH_BOT_TOKEN_FILE is required")
        access_token, refreshed = await refresh_access_token(refresh_token, client_id, client_secret)
        if token_file:
            await asyncio.to_thread(_write_token, token_file, refreshed)
        self.twitch = await Twitch(client_id, client_secret)
        try:
            if token_file:

                async def persist_refresh(_access_token: str, new_refresh_token: str) -> None:
                    await asyncio.to_thread(_write_token, token_file, new_refresh_token)

                self.twitch.user_auth_refresh_callback = persist_refresh
            await self.twitch.set_user_authentication(
                access_token,
                [AuthScope.CHAT_READ],
                refresh_token=refreshed,
            )
            self.chat = await Chat(self.twitch)
            self.chat.register_event(ChatEvent.MESSAGE, self._on_message)
        except BaseException:
            await self.twitch.close()
            self.twitch = None
            self.chat = None
            raise

    async def start(self) -> None:
        if self.chat is None:
            await self.initialize()
        chat = self.chat
        if chat is None:
            raise RuntimeError("Chat initialization did not produce a client")
        self._running = True
        chat.start()
        # Clear zombies leaked by the previous downtime BEFORE capture resumes: sessions
        # that ended while the service was down are invisible to the reconcile loop (it
        # only finalizes channels in the sink's in-memory map).
        await self._sweep_stale_sessions()
        await self._sync_channels()
        tasks = [
            asyncio.create_task(self._flush_loop()),
            asyncio.create_task(self._status_loop()),
        ]
        self._tasks = tasks
        logger.info(f"Live chat collector started for {len(self.channels)} channels")
        try:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)
            for task in done:
                if not task.cancelled() and (error := task.exception()) is not None:
                    raise error
            await asyncio.gather(*pending)
        finally:
            for task in tasks:
                if not task.done():
                    task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)
            self._tasks = []

    async def stop(self) -> None:
        async with self._stop_lock:
            if self._flush_complete and self._resources_closed:
                return
            self._running = False
            for task in self._tasks:
                task.cancel()
            await asyncio.gather(*self._tasks, return_exceptions=True)
            self._tasks = []
            flush_error: LiveMessageFlushError | None = None
            try:
                if not self._flush_complete:
                    for attempt in range(2):
                        try:
                            await self.sink.flush()
                            self._flush_complete = True
                            flush_error = None
                            break
                        except LiveMessageFlushError as error:
                            flush_error = error
                            logger.warning(
                                "Live shutdown flush attempt %s failed with %s retained rows",
                                attempt + 1,
                                error.retained_rows,
                            )
            finally:
                if not self._resources_closed:
                    if self.chat is not None:
                        self.chat.stop()
                        self.chat = None
                    if self.twitch is not None:
                        await self.twitch.close()
                        self.twitch = None
                    self._resources_closed = True
            if flush_error is not None:
                raise flush_error

    async def _stream_for(self, channel: str) -> LiveStream | None:
        twitch = self.twitch
        if twitch is None:
            raise RuntimeError("Twitch client is not initialized")
        async for stream in twitch.get_streams(user_login=[channel], first=1):
            return cast(LiveStream, stream)
        return None

    async def _on_message(self, message: ChatMessage) -> None:
        channel = message.room.name.lower() if message.room else ""
        stream = self._streams.get(channel)
        if stream is None:
            stream = await self._stream_for(channel)
            if stream is not None:
                self._streams[channel] = stream
        if stream is not None:
            await self.sink.ingest_message(message, stream)

    async def _flush_loop(self) -> None:
        while self._running:
            await asyncio.sleep(self.flush_interval)
            await self.sink.flush()

    async def _status_loop(self) -> None:
        ticks = 0
        while self._running:
            await asyncio.sleep(60)
            ticks += 1
            if ticks % _SWEEP_EVERY_TICKS == 0:
                await self._sweep_stale_sessions()
            await self._reconcile_stream_sessions()

    async def _sweep_stale_sessions(self) -> None:
        """Finalize zombie live rows (no message + no viewer sample for the stale window).

        Self-healing for restart leaks: the swept rows never got a live finalize, so they
        also never got a rollup — enqueue one per swept stream through the same retrying
        path finalized streams use. Sweep failures are logged and swallowed: a broken
        sweep must never take down live capture.
        """
        try:
            swept = await asyncio.to_thread(sweep_stale_live_sessions_db, _STALE_SESSION_HOURS)
        except Exception:
            logger.exception("Stale live-session sweep failed")
            return
        if not swept:
            return
        logger.info("Swept %s stale live session(s): %s", len(swept), swept)
        for stream_id in swept:
            self._pending_rollups.setdefault(stream_id, 0)
            await self._attempt_rollup(stream_id)

    async def _reconcile_stream_sessions(self) -> None:
        """Sync rooms, finalize ended sessions, and record rollup outcomes once."""
        await self._retry_failed_rollups()
        await self._sync_channels()
        for channel in self.channels:
            active = self.sink.active_twitch_session_id(channel)
            if active is None:
                continue
            stream = await self._stream_for(channel)
            if stream is None or int(stream.id) != active:
                await self._finalize_stream(channel)
            else:
                self._streams[channel] = stream

    async def _finalize_stream(self, channel: str) -> None:
        stream_id = await self.sink.finalize(channel)
        self._streams.pop(channel, None)
        if stream_id is None:
            return
        self._pending_rollups.setdefault(stream_id, 0)
        await self._attempt_rollup(stream_id)

    async def _retry_failed_rollups(self) -> None:
        for stream_id in list(self._pending_rollups):
            await self._attempt_rollup(stream_id)

    async def _attempt_rollup(self, stream_id: int) -> None:
        attempt = self._pending_rollups.get(stream_id, 0) + 1
        try:
            outcome = await asyncio.to_thread(compute_stream_rollup, stream_id)
            outcome.require_success()
        except Exception as error:
            if attempt >= _MAX_ROLLUP_ATTEMPTS:
                self._pending_rollups.pop(stream_id, None)
                self.rollup_failures[stream_id] = f"terminal after {attempt} attempts: {error}"
                logger.exception("Live rollup exhausted retries for stream=%s", stream_id)
            else:
                self._pending_rollups[stream_id] = attempt
                self.rollup_failures[stream_id] = str(error)
                logger.exception("Live rollup attempt %s failed for stream=%s", attempt, stream_id)
        else:
            self._pending_rollups.pop(stream_id, None)
            self.rollup_failures.pop(stream_id, None)

    async def _sync_channels(self) -> None:
        desired = set(self._static_channels)
        if self.tracking_driven:
            rows = await asyncio.to_thread(select_active_tracked_streamers_db)
            desired.update(row.twitch_username.lower() for row in rows)
        added = desired - self.channels
        removed = self.channels - desired
        if added:
            valid = {channel for channel in added if await self._ensure_creator(channel)}
            desired -= added - valid
            added = valid
            if added:
                if self.chat is None:
                    raise RuntimeError("Chat client is not initialized")
                await self.chat.join_room(sorted(added))
        if removed:
            if self.chat is None:
                raise RuntimeError("Chat client is not initialized")
            await self.chat.leave_room(sorted(removed))
            for channel in removed:
                await self._finalize_stream(channel)
        self.channels = desired

    async def _ensure_creator(self, channel: str) -> bool:
        if await asyncio.to_thread(select_creator_id_db, channel):
            return True
        twitch = self.twitch
        if twitch is None:
            raise RuntimeError("Twitch client is not initialized")
        async for user in twitch.get_users(logins=[channel]):
            creator_id = await asyncio.to_thread(
                find_or_insert_creator_id_db,
                channel,
                user.display_name,
                user.profile_image_url,
                user.id,
            )
            return creator_id is not None
        logger.warning(f"Cannot join unknown Twitch channel={channel}")
        return False
