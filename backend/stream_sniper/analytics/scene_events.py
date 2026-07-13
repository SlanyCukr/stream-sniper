"""Derive human-readable, deterministic events from one stream's rollups."""

from decimal import Decimal

from ..database.scene_event_table_gateway import (
    replace_stream_scene_events_db,
    select_stream_event_signals_db,
)


def _json_number(value):
    """Convert PostgreSQL NUMERIC values before placing them in JSON metadata."""
    return float(value) if isinstance(value, Decimal) else value


def _record_event(stream_id, creator_id, creator, occurred_at, kind, label, value):
    return {
        "event_type": "personal_record",
        "occurred_at": occurred_at,
        "creator_id": creator_id,
        "title": f"{creator} set a {label} record",
        "summary": f"{value:,.1f}" if isinstance(value, float) else f"{value:,}",
        "metadata": {"metric": kind, "value": value},
        "dedupe_key": f"stream:{stream_id}:record:{kind}",
    }


def refresh_stream_events(stream_id: int) -> int:
    header, moment, copypastas = select_stream_event_signals_db(stream_id)
    if header is None or header[5] is None:
        replace_stream_scene_events_db(stream_id, [])
        return 0
    _, creator_id, creator, stream_title, occurred_at, messages, unique, rate, prev_messages, prev_unique, prev_rate = header
    rate = _json_number(rate)
    prev_rate = _json_number(prev_rate)
    events = [{
        "event_type": "stream_report",
        "occurred_at": occurred_at,
        "creator_id": creator_id,
        "title": f"{creator} finished a stream",
        "summary": f"{messages:,} messages from {unique:,} chatters · {stream_title}",
        "metadata": {"total_messages": messages, "unique_chatters": unique, "messages_per_minute": rate},
        "dedupe_key": f"stream:{stream_id}:report",
    }]
    for kind, label, value, previous in (
        ("messages", "message", messages, prev_messages),
        ("chatters", "chatter", unique, prev_unique),
        ("rate", "chat-speed", rate, prev_rate),
    ):
        if value is not None and previous is not None and value > previous:
            events.append(_record_event(stream_id, creator_id, creator, occurred_at, kind, label, value))
    if moment and moment[1] is not None and moment[1] >= 5:
        events.append({
            "event_type": "standout_moment", "occurred_at": moment[0], "creator_id": creator_id,
            "title": f"A {moment[1]:.1f}× chat spike on {creator}",
            "summary": f"{moment[2]:,} messages in one minute",
            "metadata": {"ratio": moment[1], "message_count": moment[2]},
            "dedupe_key": f"stream:{stream_id}:moment:{moment[0]}",
        })
    for message_text_id, text, usage_count, creator_count in copypastas:
        events.append({
            "event_type": "copypasta_spread", "occurred_at": occurred_at, "creator_id": creator_id,
            "message_text_id": message_text_id,
            "title": f"A copypasta reached {creator}",
            "summary": text[:180],
            "metadata": {"usage_count": usage_count, "creator_count": creator_count},
            "dedupe_key": f"stream:{stream_id}:copypasta:{message_text_id}",
        })
    replace_stream_scene_events_db(stream_id, events)
    return len(events)
