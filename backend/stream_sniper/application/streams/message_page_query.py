"""Application query for chronological message replay pages."""

from ...database.gateways.chat.message_replay_gateway import select_stream_messages_db
from .message_models import Cursor, MessageItem, MessagePage


def get_message_page(
    stream_id: int,
    limit: int,
    *,
    after_ts: str | None,
    after_id: int | None,
    chatter_id: int | None,
    q: str | None,
    sub_only: bool,
) -> MessagePage:
    """Load one truthful keyset page, including a one-row pagination sentinel."""
    rows = select_stream_messages_db(
        stream_id,
        limit + 1,
        after_ts=after_ts,
        after_id=after_id,
        chatter_id=chatter_id,
        q=q,
        sub_only=sub_only,
    )
    has_more = len(rows) > limit
    messages = [MessageItem.from_row(row) for row in rows[:limit]]
    next_cursor = None
    if has_more:
        last = messages[-1]
        next_cursor = Cursor(after_ts=last.time, after_id=last.id)
    return MessagePage(messages=messages, next_cursor=next_cursor, has_more=has_more)
