import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime

from stream_sniper.application.tracking.models import TrackedStreamer
from stream_sniper.database.gateways.streams.records import StreamContextSample

from ..collector.twitch_api import ArchivedVideo, TwitchAPI, TwitchUpstreamError
from ..database.gateways.streams.stream_viewer_sample_table_gateway import insert_live_snapshot_db
from ..database.gateways.tracking.processing_jobs_table_gateway import enqueue_processing_job_db
from ..database.gateways.tracking.tracked_streamers_table_gateway import (
    select_active_tracked_streamers_db,
    update_tracked_streamer_check_time_db,
)
from ..logging_config import get_logger, sanitize_log_value
from ..utils.discord import deliver_discord
from .status import StreamMonitorStatus, StreamObservation

logger = get_logger(__name__)


@dataclass
class StreamStatus:
    twitch_username: str
    state: StreamObservation
    twitch_stream_session_id: int | None = None
    title: str | None = None
    started_at: datetime | None = None
    viewer_count: int | None = None
    category_id: str | None = None
    category_name: str | None = None
    language: str | None = None
    tags: list[str] | None = None
    is_mature: bool | None = None
    last_checked: datetime | None = None
    error: str | None = None

    @property
    def is_live(self) -> bool:
        return self.state is StreamObservation.LIVE


class StreamMonitor:
    def __init__(self, check_interval: int = 300, *, discord_webhook_url: str | None = None):  # 5 minutes default
        self.check_interval = check_interval
        self.twitch_api = TwitchAPI()
        self.logger = get_logger(__name__)
        self._running = False
        self._last_stream_states: dict[str, StreamObservation] = {}
        # "Went live" Discord alerting: opt-in webhook plus per-session dedup so a
        # single live session never announces twice. Sessions are forgotten when a
        # stream ends, bounding the set to concurrently-live streamers.
        self._discord_webhook_url = discord_webhook_url
        self._alerted_sessions: set[int] = set()
        self._streamer_session_ids: dict[str, int] = {}
        self._successful_checks = 0
        self._failed_checks = 0
        self._unknown_checks = 0
        self._last_cycle_completed_at: datetime | None = None
        self._last_successful_cycle: datetime | None = None

    async def initialize(self) -> None:
        """Initialize the Twitch API connection (idempotent across restarts)."""
        await self.twitch_api.ensure_initialized()
        self.logger.info("Stream monitor initialized successfully")

    async def start_monitoring(self) -> None:
        self._running = True

        try:
            while self._running:
                await self._check_all_streams()
                await asyncio.sleep(self.check_interval)
        finally:
            self._running = False

    def stop_monitoring(self) -> None:
        self._running = False

    async def close(self) -> None:
        """Stop monitoring and close the owned Twitch client."""
        self.stop_monitoring()
        await self.twitch_api.close()

    async def _check_all_streams(self) -> None:
        tracked_streamers = await asyncio.to_thread(select_active_tracked_streamers_db)

        if not tracked_streamers:
            self.logger.debug("No active tracked streamers found")
            self._finish_cycle(successful=0, failed=0, unknown=0)
            return

        self.logger.info(f"Checking {len(tracked_streamers)} tracked streamers")
        successful = 0
        failed = 0
        unknown = 0

        for streamer in tracked_streamers:
            try:
                observation = await self._check_single_stream(streamer)
            except Exception:
                failed += 1
                self.logger.exception("Error checking stream for %s", streamer.twitch_username)
            else:
                if observation is StreamObservation.UNKNOWN:
                    unknown += 1
                else:
                    successful += 1

            await asyncio.sleep(1)

        self._finish_cycle(successful=successful, failed=failed, unknown=unknown)

    def _finish_cycle(self, *, successful: int, failed: int, unknown: int) -> None:
        completed_at = datetime.now(UTC)
        self._successful_checks = successful
        self._failed_checks = failed
        self._unknown_checks = unknown
        self._last_cycle_completed_at = completed_at
        if failed == 0 and unknown == 0:
            self._last_successful_cycle = completed_at

    async def _check_single_stream(self, row: TrackedStreamer) -> StreamObservation:
        stream_status = await self._get_stream_status(row.twitch_username)

        await asyncio.to_thread(update_tracked_streamer_check_time_db, row.id, datetime.now())

        if stream_status.state is StreamObservation.UNKNOWN:
            self.logger.warning(
                "Stream state for %s is unknown; preserving previous state",
                row.twitch_username,
            )
            return StreamObservation.UNKNOWN

        if stream_status.state is StreamObservation.LIVE:
            await asyncio.to_thread(self._record_viewer_snapshot, row.id, stream_status)

        previous_state = self._last_stream_states.get(row.twitch_username, StreamObservation.UNKNOWN)
        current_state = stream_status.state
        # First non-unknown observation this process lifetime (fresh dict on restart):
        # a stream already live at first poll must not be announced as a new transition.
        is_first_observation = row.twitch_username not in self._last_stream_states

        self.logger.debug(f"Stream check for {row.twitch_username}: Previous={previous_state}, Current={current_state}")

        if previous_state is StreamObservation.LIVE and current_state is StreamObservation.OFFLINE:
            self.logger.info(f"Stream ended for {row.twitch_username}, queuing for processing")
            self._forget_alerted_session(row.twitch_username)
            await self._queue_stream_for_processing(row.id, row.twitch_username)
        elif previous_state is not StreamObservation.LIVE and current_state is StreamObservation.LIVE:
            self.logger.info(f"Stream started for {row.twitch_username}")
            await self._maybe_alert_went_live(row, stream_status, is_first_observation=is_first_observation)

        # Commit the observed state only after any ended-stream scheduling succeeds.
        self._last_stream_states[row.twitch_username] = current_state
        return current_state

    async def _maybe_alert_went_live(
        self, row: TrackedStreamer, status: StreamStatus, *, is_first_observation: bool
    ) -> None:
        """Fire a best-effort Discord "went live" alert; never affect monitoring."""
        if not self._discord_webhook_url:
            return
        # Suppress alerts for streams already live at the first poll after startup so
        # a service restart does not re-announce ongoing streams.
        if is_first_observation:
            return
        session_id = status.twitch_stream_session_id
        if session_id is None or session_id in self._alerted_sessions:
            return
        # Record before dispatch: a single session must never announce twice, even if
        # delivery fails (the offline->live edge is not revisited within a session).
        self._alerted_sessions.add(session_id)
        self._streamer_session_ids[row.twitch_username] = session_id
        try:
            await asyncio.to_thread(
                deliver_discord, self._format_live_alert(row, status), self._discord_webhook_url
            )
        except Exception as error:
            self.logger.warning(
                "Discord live alert failed for %s: %s",
                sanitize_log_value(row.twitch_username),
                sanitize_log_value(error),
            )

    @staticmethod
    def _format_live_alert(row: TrackedStreamer, status: StreamStatus) -> str:
        """Render the alert markdown, omitting missing title/category/viewer fields."""
        display_name = row.display_name or row.twitch_username
        header = f"🔴 **{display_name} is live**"
        if status.title:
            header = f"{header} — {status.title}"
        details: list[str] = []
        if status.category_name:
            details.append(status.category_name)
        if status.viewer_count is not None:
            details.append(f"{status.viewer_count} viewers")
        details.append(f"https://twitch.tv/{row.twitch_username}")
        return f"{header}\n{' · '.join(details)}"

    def _forget_alerted_session(self, twitch_username: str) -> None:
        """Drop a streamer's alerted session so the dedup set stays bounded."""
        session_id = self._streamer_session_ids.pop(twitch_username, None)
        if session_id is not None:
            self._alerted_sessions.discard(session_id)

    async def _get_stream_status(self, twitch_username: str) -> StreamStatus:
        try:
            stream_info = await self.twitch_api.get_live_stream(twitch_username)

            if stream_info:
                return StreamStatus(
                    twitch_username=twitch_username,
                    state=StreamObservation.LIVE,
                    twitch_stream_session_id=int(stream_info.id),
                    title=stream_info.title,
                    started_at=stream_info.started_at,
                    viewer_count=stream_info.viewer_count,
                    category_id=stream_info.game_id,
                    category_name=stream_info.game_name,
                    language=stream_info.language,
                    tags=list(stream_info.tags or []),
                    is_mature=stream_info.is_mature,
                    last_checked=datetime.now(),
                )
            return StreamStatus(
                twitch_username=twitch_username, state=StreamObservation.OFFLINE, last_checked=datetime.now()
            )

        except TwitchUpstreamError as e:
            self.logger.warning("Twitch status lookup failed for %s: %s", twitch_username, e)
            return StreamStatus(
                twitch_username=twitch_username,
                state=StreamObservation.UNKNOWN,
                last_checked=datetime.now(),
                error=str(e),
            )

    def _record_viewer_snapshot(self, tracked_streamer_id: int, status: StreamStatus) -> None:
        """Persist the retry-safe viewer and context snapshot pair."""
        if status.twitch_stream_session_id is None or status.viewer_count is None:
            raise ValueError("live snapshot requires twitch_stream_session_id and viewer_count")
        sampled_at = datetime.now(UTC)
        context = StreamContextSample(
            tracked_streamer_id=tracked_streamer_id,
            twitch_stream_session_id=status.twitch_stream_session_id,
            sampled_at=sampled_at,
            session_started_at=status.started_at,
            title=status.title,
            category_id=status.category_id,
            category_name=status.category_name,
            language=status.language,
            tags=status.tags,
            is_mature=status.is_mature,
        )
        insert_live_snapshot_db(
            tracked_streamer_id=tracked_streamer_id,
            twitch_stream_session_id=status.twitch_stream_session_id,
            sampled_at=sampled_at,
            viewer_count=status.viewer_count,
            title=status.title,
            session_started_at=status.started_at,
            context=context,
        )

    async def _queue_stream_for_processing(self, tracked_streamer_id: int, twitch_username: str) -> None:
        archived_videos = await self._get_recent_archived_videos(twitch_username)
        if not archived_videos:
            self.logger.warning(f"No archived videos found for {twitch_username}")
            return

        latest_video = archived_videos[0]
        twitch_vod_id = int(latest_video.twitch_vod_id)
        job_id = await asyncio.to_thread(enqueue_processing_job_db, tracked_streamer_id, twitch_vod_id)
        if job_id is None:
            self.logger.debug(f"Processing job already exists for VOD {twitch_vod_id}")
            return
        self.logger.info(f"Created processing job {job_id} for VOD {twitch_vod_id} by {twitch_username}")

    async def _get_recent_archived_videos(self, twitch_username: str, limit: int = 5) -> list[ArchivedVideo]:
        videos = await self.twitch_api.get_archived_videos(twitch_username)
        return videos[:limit] if videos else []

    async def check_streamer_now(self, twitch_username: str) -> StreamStatus:
        return await self._get_stream_status(twitch_username)

    def get_monitoring_stats(self) -> StreamMonitorStatus:
        return StreamMonitorStatus(
            running=self._running,
            check_interval=self.check_interval,
            tracked_streamers_count=len(self._last_stream_states),
            last_stream_states=self._last_stream_states.copy(),
            successful_checks=self._successful_checks,
            failed_checks=self._failed_checks,
            unknown_checks=self._unknown_checks,
            degraded=self._failed_checks > 0 or self._unknown_checks > 0,
            last_cycle_completed_at=(
                self._last_cycle_completed_at.isoformat() if self._last_cycle_completed_at else None
            ),
            last_successful_cycle=self._last_successful_cycle.isoformat() if self._last_successful_cycle else None,
        )
