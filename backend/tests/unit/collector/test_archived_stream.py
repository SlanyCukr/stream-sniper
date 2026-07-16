"""Archived-stream persistence boundary tests."""

from datetime import UTC, datetime

import pytest

from stream_sniper.collector.archived import archived_stream


def test_ensures_stream_with_duration_derived_end(monkeypatch):
    calls = []
    monkeypatch.setattr(archived_stream, "insert_stream_db", lambda *args: calls.append(args) or 7)
    started_at = datetime(2024, 1, 15, 20, tzinfo=UTC)

    assert archived_stream.ensure_archived_stream_db(123, started_at, 4, "title", "1h30m", "thumb") == 7
    assert calls == [(123, started_at, 4, "title", datetime(2024, 1, 15, 21, 30, tzinfo=UTC), "thumb")]


def test_rejects_invalid_twitch_duration():
    with pytest.raises(ValueError, match="Invalid Twitch duration"):
        archived_stream.ensure_archived_stream_db(123, datetime.now(UTC), 4, "title", "bad", "thumb")
