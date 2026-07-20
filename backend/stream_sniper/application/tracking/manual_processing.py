"""Application workflow for selecting and queueing an archived VOD."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal, Protocol

from ...database.gateways.streams.stream_table_gateway import select_existing_twitch_vod_ids_db
from ...database.gateways.tracking.processing_jobs_table_gateway import enqueue_processing_job_db
from ...database.gateways.tracking.tracked_streamers_table_gateway import select_tracked_streamer_by_id_db
from .models import TrackedStreamer


class ArchivedVod(Protocol):
    @property
    def twitch_vod_id(self) -> int: ...

    @property
    def title(self) -> str: ...


@dataclass(frozen=True)
class ManualProcessingOutcome:
    status: Literal["no_vod", "already_queued", "queued"]
    video: ArchivedVod | None = None
    job_id: int | None = None

    def __post_init__(self) -> None:
        valid = {
            "no_vod": self.video is None and self.job_id is None,
            "already_queued": self.video is not None and self.job_id is None,
            "queued": self.video is not None and self.job_id is not None,
        }
        if not valid[self.status]:
            raise ValueError(f"Invalid payload for manual processing outcome {self.status}")


def load_processing_streamer(streamer_id: int) -> TrackedStreamer | None:
    return select_tracked_streamer_by_id_db(streamer_id)


def enqueue_first_uncollected_vod(
    streamer_id: int,
    videos: Sequence[ArchivedVod],
) -> ManualProcessingOutcome:
    # One batched existence read instead of a round trip per already-collected VOD.
    collected = select_existing_twitch_vod_ids_db([int(video.twitch_vod_id) for video in videos])
    for video in videos:
        twitch_vod_id = int(video.twitch_vod_id)
        if twitch_vod_id not in collected:
            job_id = enqueue_processing_job_db(streamer_id, twitch_vod_id)
            if job_id is None:
                return ManualProcessingOutcome(status="already_queued", video=video)
            return ManualProcessingOutcome(status="queued", video=video, job_id=job_id)
    return ManualProcessingOutcome(status="no_vod")
