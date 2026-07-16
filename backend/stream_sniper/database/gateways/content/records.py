"""Scene, moment, and copypasta persistence projections."""

from typing import Any, Literal, NamedTuple, TypedDict

MomentStatus = Literal["pending", "bookmarked", "rejected", "clipped", "published"]
MomentReviewStatus = Literal["bookmarked", "rejected", "clipped", "published"]
MomentQueueStatusFilter = MomentStatus | Literal[""]
MOMENT_STATUS_PENDING: MomentStatus = "pending"


class TopPhrasePayload(TypedDict):
    phrase: str
    count: int
    lift: float


class SampleMessagePayload(TypedDict):
    text: str
    count: int


class SceneSignalHeaderRow(NamedTuple):
    stream_id: int
    creator_id: int
    creator: str
    stream_title: str
    occurred_at: str
    messages: int | None
    unique_chatters: int | None
    messages_per_minute: float | None
    previous_messages: int | None
    previous_unique_chatters: int | None
    previous_messages_per_minute: float | None


class SceneMomentSignalRow(NamedTuple):
    bucket_minute: str
    ratio: float | None
    message_count: int


class SceneCopypastaSignalRow(NamedTuple):
    message_text_id: int
    text: str
    usage_count: int
    creator_count: int


class SceneEventRow(NamedTuple):
    id: int
    event_type: str
    occurred_at: str
    creator_id: int | None
    creator_nick: str | None
    creator_display_name: str | None
    stream_id: int
    message_text_id: int | None
    title: str
    summary: str
    metadata: dict[str, Any] | None


class StreamMomentRow(NamedTuple):
    bucket_minute: str
    offset_seconds: int
    message_count: int
    baseline: float
    ratio: float | None
    unique_chatters: int
    sub_share: float | None
    emote_share: float | None
    top_phrases: list[TopPhrasePayload] | None
    sample_messages: list[SampleMessagePayload] | None
    status: MomentReviewStatus | None
    clip_url: str | None
    note: str | None


class MomentQueueRow(NamedTuple):
    stream_id: int
    title: str
    start: str
    twitch_vod_id: str | None
    creator_id: int | None
    creator_display_name: str | None
    bucket_minute: str
    offset_seconds: int
    message_count: int
    baseline: float
    ratio: float | None
    unique_chatters: int
    sub_share: float | None
    emote_share: float | None
    top_phrases: list[TopPhrasePayload] | None
    sample_messages: list[SampleMessagePayload] | None
    status: MomentReviewStatus | None
    clip_url: str | None
    note: str | None


class MomentWriteRow(NamedTuple):
    bucket_minute: str
    offset_seconds: int
    message_count: int
    baseline: float
    ratio: float | None
    unique_chatters: int
    sub_share: float | None
    emote_share: float | None
    top_phrases: list[TopPhrasePayload] | None
    sample_messages: list[SampleMessagePayload] | None


class SceneLeaderboardRow(NamedTuple):
    creator_id: int
    nick: str
    display_name: str
    profile_image_url: str | None
    streams: int
    hours_streamed: float | None
    total_messages: int
    msgs_per_min: float | None
    chatter_appearances: int


class ScenePeakViewerRow(NamedTuple):
    creator_id: int
    peak_viewers: int


class SceneCopypastaRow(NamedTuple):
    message_text_id: int
    text: str
    usage_count: int
    chatter_appearances: int
    stream_count: int
    creator_count: int
    first_seen: str | None
    last_stream_start: str | None


class CopypastaOccurrenceRow(NamedTuple):
    stream_id: int
    creator_id: int
    nick: str
    display_name: str
    profile_image_url: str | None
    stream_title: str
    stream_start: str | None
    first_seen: str | None
    usage_count: int
    chatter_count: int


class CopypastaContextRow(NamedTuple):
    id: int
    time: str
    chatter_id: int
    nick: str
    text: str


class SceneEventWrite(TypedDict):
    event_type: str
    occurred_at: str
    creator_id: int
    message_text_id: int | None
    title: str
    summary: str
    metadata: dict[str, Any]
    dedupe_key: str
