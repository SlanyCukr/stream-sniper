"""Read contract for the chatter head-to-head (the /versus/chatters page).

Follows the creator head-to-head conventions: the pair is normalized to
(lo, hi) by the HTTP layer, so side ``a`` is always the lower chatter id.
"""

from pydantic import BaseModel, Field

from .passport_models import PassportArchetype, PassportHomeChannel


class VersusChatter(BaseModel):
    """One side of the comparison: lifetime aggregates for a single chatter."""

    chatter_id: int
    nick: str
    is_bot: bool | None = Field(None, description="Null = not yet classified (nullable-means-unknown)")
    messages: int
    streams_attended: int
    creators_visited: int
    first_seen: str | None = Field(None, description="Lifetime first MESSAGE time (ISO 8601)")
    last_seen: str | None = Field(None, description="Lifetime last MESSAGE time (ISO 8601)")
    home_channel: PassportHomeChannel | None = Field(None, description="The creator they chat in most")
    archetypes: list[PassportArchetype] = Field(..., description="Same badge rules as the passport")


class ChatterHeadToHead(BaseModel):
    """Pairwise chatter comparison. Never-crossed-paths is a legitimate zero, not an error."""

    a: VersusChatter
    b: VersusChatter
    shared_streams: int = Field(..., description="Streams both chatters attended")
    shared_creators: int = Field(..., description="Distinct channels those shared streams span")
