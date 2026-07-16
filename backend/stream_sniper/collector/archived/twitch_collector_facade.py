from collections.abc import Callable
from dataclasses import dataclass

from ...logging_config import PerformanceTimer, get_logger
from ..twitch_api import SyncTwitchClient
from .creator_resolver import CreatorResolver
from .twitch_vod_chat_downloader import TwitchVodChatDownloader
from .vod_ingestion import VodIngestionPipeline, VodIngestionResult


@dataclass(frozen=True)
class CollectorRunResult:
    processed_vods: tuple[VodIngestionResult, ...]

    @property
    def processed_count(self) -> int:
        return len(self.processed_vods)


class TwitchCollectorFacade:
    def __init__(
        self,
        twitch_username: str,
        *,
        twitch_vod_id: int | None = None,
        twitch_client: SyncTwitchClient | None = None,
        creator_resolver: CreatorResolver | None = None,
        vod_source_factory: Callable[[str, SyncTwitchClient, int | None], TwitchVodChatDownloader] = (
            TwitchVodChatDownloader
        ),
        pipeline_factory: Callable[[int, str], VodIngestionPipeline] = VodIngestionPipeline,
    ) -> None:
        self.twitch_username = twitch_username
        self.logger = get_logger(__name__)
        self.creator_id = -1

        self.twitch_client = twitch_client or SyncTwitchClient()
        try:
            self.twitch_client.initialize()
            self.creator_id = (creator_resolver or CreatorResolver()).resolve(twitch_username, self.twitch_client)
            self.chat_downloader = vod_source_factory(twitch_username, self.twitch_client, twitch_vod_id)
            self.pipeline = pipeline_factory(self.creator_id, twitch_username)
        except BaseException:
            self.twitch_client.close()
            raise

    def ingest_archived_vods(self, max_vods: int | None = None) -> CollectorRunResult:
        with PerformanceTimer(
            self.logger,
            "archived_vod_ingestion",
            slow_threshold=10.0,
        ):
            return self._ingest_archived_vods(max_vods)

    def _ingest_archived_vods(self, max_vods: int | None) -> CollectorRunResult:
        """Ingest archived VODs until the source is exhausted or the limit is reached."""
        processed_vods: list[VodIngestionResult] = []

        try:
            while True:
                if max_vods is not None and len(processed_vods) >= max_vods:
                    self.logger.info("Reached max_vods=%s; stopping archived VOD ingestion", max_vods)
                    break
                vod_chat = self.chat_downloader.open_chat_stream()
                if vod_chat is None:
                    break

                result = self.pipeline.ingest(vod_chat)
                processed_vods.append(result)
        finally:
            self.logger.info(f"Archived VOD ingestion completed. Total VODs ingested: {len(processed_vods)}")
            self.close()
        return CollectorRunResult(processed_vods=tuple(processed_vods))

    def close(self) -> None:
        """Close the collector-owned Twitch client loop and HTTP session."""
        self.twitch_client.close()
