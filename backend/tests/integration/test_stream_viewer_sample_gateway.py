"""PostgreSQL integration tests for viewer samples (session anchor, windowing, and timezone).

Self-provisioning like test_analytics_expansion_gateways.py: the base ``db_cursor`` fixture only
knows the baseline tables, so ``viewer_db`` here creates ``tracked_streamers`` and
``stream_viewer_sample`` (CREATE ... IF NOT EXISTS, no FKs needed for the read path) and truncates
them per test. Samples carry no stream/VOD id, so linkage is creator-level via
tracked_streamers.creator_id plus a time anchor — see the gateway docstring.

All timestamptz literals carry an explicit UTC offset so the comparison is deterministic regardless
of the test server's session TimeZone.
"""

import pytest

from stream_sniper.database.gateways.streams.stream_viewer_sample_table_gateway import select_stream_viewer_samples_db
from tests.conftest import create_test_creator, create_test_stream

_VIEWER_DDL = """
SET search_path TO stream_sniper;
CREATE TABLE IF NOT EXISTS tracked_streamers (
    id serial PRIMARY KEY,
    creator_id int NOT NULL,
    twitch_username varchar(255) NOT NULL,
    display_name varchar(255) NOT NULL,
    is_active boolean NOT NULL DEFAULT true,
    processing_enabled boolean NOT NULL DEFAULT true,
    created_at timestamp NOT NULL DEFAULT current_timestamp,
    updated_at timestamp NOT NULL DEFAULT current_timestamp,
    CONSTRAINT tracked_streamers_creator_id_uindex UNIQUE (creator_id),
    CONSTRAINT tracked_streamers_twitch_username_uindex UNIQUE (twitch_username)
);
CREATE TABLE IF NOT EXISTS stream_viewer_sample (
    id bigserial PRIMARY KEY,
    tracked_streamer_id int NOT NULL,
    twitch_stream_session_id bigint NOT NULL,
    sampled_at timestamptz NOT NULL,
    viewer_count int NOT NULL,
    title text NULL,
    session_started_at timestamptz NULL,
    CONSTRAINT stream_viewer_sample_uq UNIQUE (tracked_streamer_id, twitch_stream_session_id, sampled_at)
);
"""


@pytest.fixture
def viewer_db(db_cursor):
    db_cursor.execute(_VIEWER_DDL)
    db_cursor.execute("TRUNCATE stream_viewer_sample, tracked_streamers RESTART IDENTITY CASCADE")
    db_cursor.connection.commit()
    return db_cursor


def _tracked_streamer(cursor, creator_id, username="tracked_user"):
    cursor.execute(
        "INSERT INTO tracked_streamers (creator_id, twitch_username, display_name) VALUES (%s, %s, %s) RETURNING id",
        (creator_id, username, username),
    )
    return cursor.fetchone()[0]


def _sample(cursor, tsid, session_id, sampled_at, viewer_count, session_started_at=None):
    cursor.execute(
        "INSERT INTO stream_viewer_sample "
        "(tracked_streamer_id, twitch_stream_session_id, sampled_at, viewer_count, session_started_at) "
        "VALUES (%s, %s, %s, %s, %s)",
        (tsid, session_id, sampled_at, viewer_count, session_started_at),
    )


# Base stream spans 20:00–23:00 UTC -> window is [19:50, 23:30].
_START = "2024-01-15 20:00:00"
_END = "2024-01-15 23:00:00"


def _stream(cursor, creator_id):
    return create_test_stream(
        cursor,
        {"twitch_id": 701, "title": "vs", "start": _START, "end": _END},
        creator_id,
    )


class TestViewerSamples:
    def test_session_anchor_picks_closest_within_15min(self, viewer_db):
        creator_id = create_test_creator(viewer_db)
        tsid = _tracked_streamer(viewer_db, creator_id)
        stream_id = _stream(viewer_db, creator_id)

        # Session A starts 20:05 (5 min after stream start) -> closer than B at 20:12 (12 min).
        _sample(viewer_db, tsid, 1001, "2024-01-15 20:06:00+00", 100, "2024-01-15 20:05:00+00")
        _sample(viewer_db, tsid, 1001, "2024-01-15 20:30:00+00", 200, "2024-01-15 20:05:00+00")
        _sample(viewer_db, tsid, 1002, "2024-01-15 20:15:00+00", 999, "2024-01-15 20:12:00+00")
        viewer_db.connection.commit()

        rows = select_stream_viewer_samples_db(stream_id)
        assert [r[1] for r in rows] == [100, 200]  # only session A; B's 999 excluded
        assert [r[0] for r in rows] == ["2024-01-15T20:06:00", "2024-01-15T20:30:00"]

    def test_winning_session_samples_clamped_to_window(self, viewer_db):
        creator_id = create_test_creator(viewer_db)
        tsid = _tracked_streamer(viewer_db, creator_id)
        stream_id = _stream(viewer_db, creator_id)

        # One anchored session, but a sample past win_end (23:30) must be clamped out.
        _sample(viewer_db, tsid, 3001, "2024-01-15 20:06:00+00", 100, "2024-01-15 20:05:00+00")
        _sample(viewer_db, tsid, 3001, "2024-01-15 23:45:00+00", 300, "2024-01-15 20:05:00+00")
        viewer_db.connection.commit()

        rows = select_stream_viewer_samples_db(stream_id)
        assert [r[1] for r in rows] == [100]

    def test_falls_back_to_time_window_when_session_started_at_null(self, viewer_db):
        creator_id = create_test_creator(viewer_db)
        tsid = _tracked_streamer(viewer_db, creator_id)
        stream_id = _stream(viewer_db, creator_id)

        # No session has session_started_at -> no anchor; every windowed sample returned.
        _sample(viewer_db, tsid, 2001, "2024-01-15 20:06:00+00", 100, None)
        _sample(viewer_db, tsid, 2002, "2024-01-15 20:20:00+00", 200, None)
        viewer_db.connection.commit()

        rows = select_stream_viewer_samples_db(stream_id)
        assert [r[1] for r in rows] == [100, 200]

    def test_samples_outside_window_excluded(self, viewer_db):
        creator_id = create_test_creator(viewer_db)
        tsid = _tracked_streamer(viewer_db, creator_id)
        stream_id = _stream(viewer_db, creator_id)

        _sample(viewer_db, tsid, 4001, "2024-01-15 19:40:00+00", 50, None)  # before win_start 19:50
        _sample(viewer_db, tsid, 4001, "2024-01-15 20:06:00+00", 100, None)  # inside
        _sample(viewer_db, tsid, 4001, "2024-01-15 23:45:00+00", 300, None)  # after win_end 23:30
        viewer_db.connection.commit()

        rows = select_stream_viewer_samples_db(stream_id)
        assert [r[1] for r in rows] == [100]

    def test_timestamptz_compared_and_returned_as_utc(self, viewer_db):
        creator_id = create_test_creator(viewer_db)
        tsid = _tracked_streamer(viewer_db, creator_id)
        stream_id = _stream(viewer_db, creator_id)

        # 22:05+02 == 20:05 UTC (inside window); 21:45+02 == 19:45 UTC (before 19:50, excluded).
        # A naive (non-UTC) comparison would mis-window these; the AT TIME ZONE 'UTC' cast fixes it.
        _sample(viewer_db, tsid, 5001, "2024-01-15 22:05:00+02", 100, None)
        _sample(viewer_db, tsid, 5001, "2024-01-15 21:45:00+02", 50, None)
        viewer_db.connection.commit()

        rows = select_stream_viewer_samples_db(stream_id)
        assert rows == [("2024-01-15T20:05:00", 100)]

    def test_session_started_at_beyond_15min_is_not_an_anchor(self, viewer_db):
        creator_id = create_test_creator(viewer_db)
        tsid = _tracked_streamer(viewer_db, creator_id)
        stream_id = _stream(viewer_db, creator_id)

        # Only session's start is 40 min after stream start (> ±15 min) -> no anchor, fall back to
        # the whole time window (the sample itself is still inside it).
        _sample(viewer_db, tsid, 6001, "2024-01-15 20:41:00+00", 100, "2024-01-15 20:40:00+00")
        viewer_db.connection.commit()

        rows = select_stream_viewer_samples_db(stream_id)
        assert [r[1] for r in rows] == [100]
