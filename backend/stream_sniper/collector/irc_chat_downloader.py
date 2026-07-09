from typing import Any, Iterator, Optional, Tuple

from chat_downloader import ChatDownloader

from ..database.stream_table_gateway import select_stream_by_twitch_id_db
from ..logging_config import get_logger
from . import twitch_gql_patch  # noqa: F401  (import applies the VideoMetadata GQL patch)
from .twitch_api import TwitchAPI


class IrcChatDownloader:
    def __init__(self, nickname: str, twitch_api: TwitchAPI):
        self.nickname = nickname
        self.logger = get_logger(__name__)
        # Use the caller's TwitchAPI instance, NOT TwitchAPI.instance(). The
        # singleton is the first instance ever created; in the tracking service
        # that's the stream monitor's, whose streamer_nickname it rewrites on
        # every poll — so instance().get_available_video_ids() would return a
        # different streamer's VODs than the one this collector is processing.
        self.available_video_ids = twitch_api.get_available_video_ids()
        self.downloader = ChatDownloader()
        self.logger.info(
            f"IRC chat downloader initialized for {nickname} with {len(self.available_video_ids)} available videos"
        )

    def download_chat(
        self,
    ) -> Tuple[Optional[Iterator[dict]], Optional[str], Optional[str], Optional[str], Optional[str], Optional[str]]:
        """Return a lazy chat iterator + VOD metadata for the next unprocessed video.

        The chat is NOT materialized here — a full VOD from a large streamer can
        be millions of messages, which OOMs the RPI. The caller iterates (and
        batches) the messages instead. Returns an all-None tuple when no
        unprocessed videos remain.
        """
        while True:
            # no available videos
            if len(self.available_video_ids) == 0:
                return None, None, None, None, None, None

            currently_processed_video: Any = self.available_video_ids.pop(0)

            # available video was already processed - is in the database
            if select_stream_by_twitch_id_db(currently_processed_video.id):
                self.logger.debug("Available video is already processed - is in the database.")
                continue

            video_id = currently_processed_video.id
            self.logger.info(f"Downloading chat for video with ID {video_id}")

            try:
                # Note: message_receive_timeout is deliberately NOT set — it
                # only applies to live IRC sockets, never the VOD GQL path
                # this collector uses (an earlier 0.01 value here was a red
                # herring while chasing truncated captures; the real fix is
                # the null-comments retry in twitch_gql_patch).
                chat = self.downloader.get_chat(
                    f"https://www.twitch.tv/videos/{video_id}",
                    format="json",
                    buffer_size=16384,
                    # The collector runs in a worker thread inside a container:
                    # chat_downloader's default interactive retry prompt uses
                    # signal-based timed stdin, which raises PermissionError off
                    # the main thread. Fall back to plain back-off retries.
                    interruptible_retry=False,
                )
            except Exception as e:
                self.logger.error(f"Failed to start chat download for video {video_id}: {e}", exc_info=True)
                continue

            returned_tuple = (
                iter(chat),
                currently_processed_video.id,
                currently_processed_video.created_at,
                currently_processed_video.title,
                currently_processed_video.duration,
                currently_processed_video.thumbnail_url,
            )

            return returned_tuple
