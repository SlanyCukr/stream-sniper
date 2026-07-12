"""Response models for per-stream insight endpoints (mentions, emotes, phrases)."""

from typing import List, Optional

from pydantic import BaseModel


class MentionedChatter(BaseModel):
    """A chatter mentioned via @nick in a stream, with total mention count."""

    chatter_id: int
    nick: Optional[str]
    count: int


class MentionPair(BaseModel):
    """A directed mention edge: `from` chatter mentioned `to` chatter `count` times."""

    from_chatter_id: int
    from_nick: Optional[str]
    to_chatter_id: int
    to_nick: Optional[str]
    count: int


class StreamMentions(BaseModel):
    """Most-mentioned chatters plus the top directed mention pairs for one stream."""

    mentioned: List[MentionedChatter]
    pairs: List[MentionPair]


class EmoteStat(BaseModel):
    """Per-stream emote usage from the rollup-computed stream_emote_stats table."""

    name: str
    source: str  # 'bttv' or 'twitch'
    provider_id: Optional[str]  # CDN id; None when unknown / failed validation
    usage_count: int
    chatter_count: int


class StreamEmotes(BaseModel):
    """Top emotes used in one stream."""

    emotes: List[EmoteStat]


class CreatorEmoteStat(EmoteStat):
    """Emote usage summed across all of one creator's streams."""

    stream_count: int  # distinct streams the emote appeared in


class CreatorEmotes(BaseModel):
    """Top emotes across all of a creator's streams."""

    emotes: List[CreatorEmoteStat]


class PhraseStat(BaseModel):
    """A recurring phrase (1-2 gram) from the rollup-computed stream_phrase_stats table."""

    phrase: str
    usage_count: int
    chatter_count: int


class StreamPhrases(BaseModel):
    """Top recurring phrases in one stream."""

    phrases: List[PhraseStat]
