"""Stream-wide analytics persistence projections."""

from typing import NamedTuple


class StreamMetricsRow(NamedTuple):
    total_messages: int | None
    unique_chatters: int | None
    duration_seconds: int | None
    messages_per_minute: float | None
    peak_messages: int | None
    peak_bucket_minute: str | None
    new_chatters: int | None
    returning_chatters: int | None
    sub_messages: int | None
    emote_messages: int | None


class StreamHeaderRow(NamedTuple):
    start: str
    twitch_vod_id: str


class StreamBucketRow(NamedTuple):
    bucket_minute: str
    message_count: int
    unique_chatters: int
    sub_messages: int | None
    emote_messages: int | None


class TopEmoteRow(NamedTuple):
    name: str
    source: str
    provider_id: str | None
    usage_count: int
    chatter_count: int


class CreatorEmoteRow(NamedTuple):
    name: str
    source: str
    provider_id: str | None
    usage_count: int
    chatter_count: int
    stream_count: int


class TopPhraseRow(NamedTuple):
    phrase: str
    usage_count: int
    chatter_count: int


class CreatorReportRow(NamedTuple):
    stream_id: int
    start: str | None
    duration_seconds: int | None
    total_messages: int | None
    messages_per_minute: float | None
    unique_chatters: int | None
    new_chatters: int | None
    returning_chatters: int | None
    sub_messages: int | None
    peak_messages: int | None


class CreatorTrendRow(NamedTuple):
    stream_id: int
    title: str
    start: str
    duration_seconds: int | None
    message_count: int
    messages_per_minute: float
    unique_chatters: int
    new_chatters: int
    returning_chatters: int


class StreamCompareHeaderRow(NamedTuple):
    stream_id: int
    creator_id: int
    creator_nick: str
    creator_display_name: str
    title: str
    start: str | None
    duration_seconds: int | None
    total_messages: int | None
    messages_per_minute: float | None
    unique_chatters: int | None
    new_chatters: int | None
    returning_chatters: int | None
    sub_messages: int | None
    emote_messages: int | None
    peak_messages: int | None
    peak_bucket_minute: str | None


class StreamCompareBucketRow(NamedTuple):
    stream_id: int
    bucket_minute: str
    message_count: int
    unique_chatters: int


class StreamPairRetentionRow(NamedTuple):
    from_stream_id: int
    to_stream_id: int
    from_audience: int
    to_audience: int
    retained: int


class ChatterDebutRow(NamedTuple):
    """A chatter's first message in the corpus, from the stream_chatter_stats rollup."""

    stream_id: int
    stream_title: str
    creator_display_name: str
    time: str


class ChatterActiveStreamRow(NamedTuple):
    """The stream a chatter sent the most messages in, from the stream_chatter_stats rollup."""

    stream_id: int
    title: str
    creator_display_name: str
    message_count: int


class ChatterTimeBoundsRow(NamedTuple):
    """Lifetime first/last MESSAGE times for a chatter, from the stream_chatter_stats rollup.

    Message times, not stream-start times — a chatter whose first message landed three
    hours into a stream is first seen at that message, not at the stream's start."""

    first_message_time: str | None
    last_message_time: str | None
