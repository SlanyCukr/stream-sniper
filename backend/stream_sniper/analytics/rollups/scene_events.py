"""Derive human-readable, deterministic events from one stream's rollups."""

from decimal import Decimal
from typing import Any

from stream_sniper.database.gateways.content.records import (
    SceneCopypastaSignalRow,
    SceneEventWrite,
    SceneMomentSignalRow,
    SceneSignalHeaderRow,
)

from ...database.gateways.content.scene_event_table_gateway import (
    replace_stream_scene_events_db,
    select_stream_event_signals_db,
)


def _json_number(value: Any) -> Any:
    """Convert PostgreSQL NUMERIC values before placing them in JSON metadata."""
    return float(value) if isinstance(value, Decimal) else value


def _record_event(
    stream_id: int,
    creator_id: int,
    creator: str,
    occurred_at: str,
    kind: str,
    label: str,
    value: Any,
) -> SceneEventWrite:
    return {
        "event_type": "personal_record",
        "occurred_at": occurred_at,
        "creator_id": creator_id,
        "message_text_id": None,
        "title": f"{creator} set a {label} record",
        "summary": f"{value:,.1f}" if isinstance(value, float) else f"{value:,}",
        "metadata": {"metric": kind, "value": value},
        "dedupe_key": f"stream:{stream_id}:record:{kind}",
    }


def _report_event(stream_id: int, header: SceneSignalHeaderRow, rate: float | None) -> SceneEventWrite:
    return {
        "event_type": "stream_report",
        "occurred_at": header.occurred_at,
        "creator_id": header.creator_id,
        "message_text_id": None,
        "title": f"{header.creator} finished a stream",
        "summary": f"{header.messages:,} messages from {header.unique_chatters:,} chatters · {header.stream_title}",
        "metadata": {
            "total_messages": header.messages,
            "unique_chatters": header.unique_chatters,
            "messages_per_minute": rate,
        },
        "dedupe_key": f"stream:{stream_id}:report",
    }


def _standout_event(
    stream_id: int,
    creator_id: int,
    creator: str,
    moment: SceneMomentSignalRow,
) -> SceneEventWrite:
    return {
        "event_type": "standout_moment",
        "occurred_at": moment.bucket_minute,
        "creator_id": creator_id,
        "message_text_id": None,
        "title": f"A {moment.ratio:.1f}× chat spike on {creator}",
        "summary": f"{moment.message_count:,} messages in one minute",
        "metadata": {"ratio": moment.ratio, "message_count": moment.message_count},
        "dedupe_key": f"stream:{stream_id}:moment:{moment.bucket_minute}",
    }


def _copypasta_event(
    stream_id: int,
    header: SceneSignalHeaderRow,
    copypasta: SceneCopypastaSignalRow,
) -> SceneEventWrite:
    return {
        "event_type": "copypasta_spread",
        "occurred_at": header.occurred_at,
        "creator_id": header.creator_id,
        "message_text_id": copypasta.message_text_id,
        "title": f"A copypasta reached {header.creator}",
        "summary": copypasta.text[:180],
        "metadata": {
            "usage_count": copypasta.usage_count,
            "creator_count": copypasta.creator_count,
        },
        "dedupe_key": f"stream:{stream_id}:copypasta:{copypasta.message_text_id}",
    }


def refresh_stream_events(stream_id: int) -> int:
    header, moment, copypastas = select_stream_event_signals_db(stream_id)
    if header is None or header.messages is None:
        replace_stream_scene_events_db(stream_id, [])
        return 0
    rate = _json_number(header.messages_per_minute)
    previous_rate = _json_number(header.previous_messages_per_minute)
    events = [_report_event(stream_id, header, rate)]
    for kind, label, value, previous in (
        ("messages", "message", header.messages, header.previous_messages),
        ("chatters", "chatter", header.unique_chatters, header.previous_unique_chatters),
        ("rate", "chat-speed", rate, previous_rate),
    ):
        if value is not None and previous is not None and value > previous:
            events.append(
                _record_event(
                    stream_id,
                    header.creator_id,
                    header.creator,
                    header.occurred_at,
                    kind,
                    label,
                    value,
                )
            )
    if moment and moment.ratio is not None and moment.ratio >= 5:
        events.append(_standout_event(stream_id, header.creator_id, header.creator, moment))
    events.extend(_copypasta_event(stream_id, header, copypasta) for copypasta in copypastas)
    replace_stream_scene_events_db(stream_id, events)
    return len(events)
