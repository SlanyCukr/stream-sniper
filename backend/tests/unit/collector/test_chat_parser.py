"""Typed chat normalization contract tests."""

from datetime import UTC, datetime

import pytest

from stream_sniper.collector.archived.chat_parser import TwitchChatParser


def _author(name: str | None, *, subscriber: bool = False, badges=None):
    return {
        "id": None,
        "name": name,
        "display_name": name,
        "badges": badges or [],
        "is_subscriber": subscriber,
    }


def test_parse_batch_returns_explicit_lines_and_deduplicated_inputs():
    batch = TwitchChatParser().parse_batch(
        [
            {
                "author": _author(
                    "viewer",
                    subscriber=True,
                    badges=[{"name": "subscriber", "version": "6"}],
                ),
                "message": "Kappa",
                "timestamp": 1_642_287_015_000_000,
                "emotes": [{"id": "25", "name": "Kappa"}],
            },
            {"author": _author("viewer"), "message": "Kappa", "timestamp": 1_642_287_016_000_000},
            {"author": _author(None), "message": "hello", "timestamp": 1_642_287_017_000_000},
        ]
    )

    assert len(batch.lines) == 3
    assert batch.unique_nicks == ("Unknown", "viewer")
    assert batch.unique_messages == ("Kappa", "hello")
    assert batch.emotes == (("Kappa", "25"),)
    assert batch.lines[0].timestamp == datetime.fromtimestamp(1_642_287_015, UTC)
    assert batch.lines[0].is_subscriber is True
    assert batch.lines[0].badges == "subscriber/6"


def test_each_parse_has_no_mutable_emote_side_channel():
    processor = TwitchChatParser()
    first = processor.parse_batch(
        [{"author": _author("a"), "message": "Old", "timestamp": 1, "emotes": [{"id": "1", "name": "Old"}]}]
    )
    second = processor.parse_batch(
        [{"author": _author("b"), "message": "New", "timestamp": 2, "emotes": [{"id": "2", "name": "New"}]}]
    )

    assert first.emotes == (("Old", "1"),)
    assert second.emotes == (("New", "2"),)


@pytest.mark.parametrize(
    "payload",
    [
        {"author": _author("viewer"), "message": "missing timestamp"},
        {"author": _author("viewer"), "message": 7, "timestamp": 1},
        {"author": "viewer", "message": "bad author", "timestamp": 1},
    ],
)
def test_malformed_required_chat_fields_fail_at_normalization(payload):
    with pytest.raises((KeyError, TypeError, ValueError)):
        TwitchChatParser().parse_batch([payload])


def test_large_batch_keeps_all_lines_but_deduplicates_lookup_inputs():
    chat = [
        {"author": _author(f"user_{index % 100}"), "message": f"message_{index}", "timestamp": index}
        for index in range(1000)
    ]

    batch = TwitchChatParser().parse_batch(chat)

    assert len(batch.lines) == 1000
    assert len(batch.unique_nicks) == 100
    assert len(batch.unique_messages) == 1000
