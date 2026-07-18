"""Twitch archived-VOD chat selection and lazy download boundary."""

from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime

from ...analytics.rollups.rollup_engine import compute_stream_rollup
from ...database.gateways.chat.live_chat_table_gateway import (
    reconcile_live_stream_vod_db,
    select_live_stream_by_session_db,
)
from ...database.gateways.streams.stream_table_gateway import stream_exists_by_twitch_vod_id_db
from ...logging_config import get_logger
from ..twitch_api import ArchivedVideo, SyncTwitchClient
from .archived_stream import _stopped_at
from .twitch_archived_chat import ArchivedChatMessage, TwitchArchivedChatClient


def _vod_ended_at(video: ArchivedVideo) -> datetime | None:
    """The VOD's authoritative session end (created_at + duration) as a naive-UTC datetime.

    None when Twitch's duration string is missing/unparseable — reconciliation then simply
    keeps the recorded end.
    """
    try:
        ended_at = _stopped_at(video.created_at, video.duration)
    except ValueError:
        return None
    if ended_at.tzinfo is not None:
        ended_at = ended_at.astimezone(UTC).replace(tzinfo=None)
    return ended_at


@dataclass(frozen=True)
class VodChatStream:
    messages: Iterator[ArchivedChatMessage]
    twitch_vod_id: int
    started_at: datetime
    title: str
    duration: str
    thumbnail_url: str


class VodChatDownloadError(RuntimeError):
    """Raised when Twitch exposes a VOD but its chat download cannot start."""


class TwitchVodChatDownloader:
    def __init__(
        self,
        twitch_username: str,
        twitch_client: SyncTwitchClient,
        twitch_vod_id: int | None = None,
    ) -> None:
        self.twitch_username = twitch_username
        self._requested_vod_id = twitch_vod_id
        self.logger = get_logger(__name__)
        available_videos = twitch_client.get_archived_videos(twitch_username)
        self.available_videos = (
            [video for video in available_videos if video.twitch_vod_id == twitch_vod_id]
            if twitch_vod_id is not None
            else available_videos
        )
        if twitch_vod_id is not None and not self.available_videos:
            raise VodChatDownloadError(f"Requested Twitch VOD {twitch_vod_id} is unavailable for {twitch_username}")
        self.chat_client = TwitchArchivedChatClient()
        self.logger.info(
            "Twitch VOD chat downloader initialized for %s with %s archived videos",
            twitch_username,
            len(self.available_videos),
        )

    def open_chat_stream(self) -> VodChatStream | None:
        """Return the next new VOD, or reopen an explicitly requested VOD for retry."""
        while self.available_videos:
            video: ArchivedVideo = self.available_videos.pop(0)

            if video.twitch_stream_session_id:
                captured = select_live_stream_by_session_db(video.twitch_stream_session_id)
                if captured and captured[1]:
                    reconciled = reconcile_live_stream_vod_db(
                        video.twitch_stream_session_id,
                        video.twitch_vod_id,
                        video.thumbnail_url,
                        _vod_ended_at(video),
                    )
                    self.logger.info(
                        "Skipping VOD %s; session %s was captured live",
                        video.twitch_vod_id,
                        video.twitch_stream_session_id,
                    )
                    if reconciled is not None and reconciled[1]:
                        # The VOD's end extended a provisional (swept-zombie) end, so every
                        # duration-derived rollup metric is stale — recompute in place.
                        stream_id = reconciled[0]
                        self.logger.info("VOD %s repaired stream %s end; recomputing rollup", video.twitch_vod_id, stream_id)
                        try:
                            compute_stream_rollup(stream_id).require_success()
                        except Exception:
                            self.logger.exception("Rollup recompute failed for repaired stream %s", stream_id)
                    continue

            discovery_mode = getattr(self, "_requested_vod_id", None) is None
            if discovery_mode and stream_exists_by_twitch_vod_id_db(video.twitch_vod_id):
                self.logger.debug("Archived video is already processed")
                continue

            self.logger.info("Downloading chat for Twitch VOD %s", video.twitch_vod_id)
            try:
                chat = self.chat_client.open_messages(video.twitch_vod_id)
            except Exception as exc:
                self.logger.exception("Failed to start chat download for Twitch VOD %s", video.twitch_vod_id)
                raise VodChatDownloadError(
                    f"Failed to start chat download for Twitch VOD {video.twitch_vod_id}"
                ) from exc

            return VodChatStream(
                messages=iter(chat),
                twitch_vod_id=video.twitch_vod_id,
                started_at=video.created_at,
                title=video.title,
                duration=video.duration,
                thumbnail_url=video.thumbnail_url,
            )

        return None
