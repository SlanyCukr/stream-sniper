"""Response contracts for chatter lookup and activity endpoints."""


from pydantic import BaseModel, Field


class ChatterMessage(BaseModel):
    stream_id: int
    stream_title: str
    creator_display_name: str
    text: str
    timestamp: str


class ChatterIdentity(BaseModel):
    chatter_id: int
    is_bot: bool | None


class ChatterSearchResult(BaseModel):
    chatter_id: int
    nick: str
    is_bot: bool | None


class ChatterActivity(BaseModel):
    stream_id: int
    stream_title: str
    start: str
    creator_id: int
    creator_display_name: str
    message_count: int
    is_bot: bool | None


class ChatterMessagesResponse(BaseModel):
    """Paginated cross-stream chatter message log."""

    messages: list[ChatterMessage] = Field(..., description="Named messages with their stream context")
    total: int = Field(
        ...,
        description="Total messages sent by the chatter",
        json_schema_extra={"example": 1234},
    )
    offset: int = Field(..., description="Current zero-based row offset")
    limit: int = Field(..., description="Maximum messages returned by this page")
