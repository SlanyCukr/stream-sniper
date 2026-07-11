"""Integration tests for the analytics rollup engine (MASTER_PLAN §9.1).

Gated on a reachable Postgres (via the session-scoped ``test_db_connection`` fixture,
same as the other integration tests). Unlike ``db_cursor`` this test does NOT truncate
the shared tables — it creates its own uniquely-named creator/streams/chatters, runs the
rollup, asserts, and cleans up only its own rows, so it is safe to run alongside seeded
verification data.

The rollup engine reads/writes through the connection pool, which conftest points at the
same database as ``test_db_connection`` (POSTGRES_* == TEST_DB_*). ``test_db_connection``
is autocommit, so rows we insert are immediately visible to the pool's own connection.
"""

from datetime import datetime, timedelta

import pytest

CREATOR_NICK = "itest_rollup_creator"
MSG_TEXT = "itest_rollup_msg"

# The analytics rollup tables (revision 0006). Created IF NOT EXISTS so the test is
# self-provisioning against any reachable database, regardless of migration state.
_ANALYTICS_DDL = """
SET search_path TO stream_sniper;
CREATE TABLE IF NOT EXISTS stream_time_bucket (
    stream_id int NOT NULL, bucket_minute timestamp NOT NULL,
    message_count int NOT NULL, unique_chatters int NOT NULL,
    CONSTRAINT stream_time_bucket_pk PRIMARY KEY (stream_id, bucket_minute)
);
CREATE TABLE IF NOT EXISTS stream_chatter_stats (
    stream_id int NOT NULL, chatter_id int NOT NULL, message_count int NOT NULL,
    first_message_time timestamp NULL, last_message_time timestamp NULL,
    CONSTRAINT stream_chatter_stats_pk PRIMARY KEY (stream_id, chatter_id)
);
CREATE TABLE IF NOT EXISTS stream_metrics (
    stream_id int PRIMARY KEY, total_messages int NOT NULL, unique_chatters int NOT NULL,
    duration_seconds int NULL, messages_per_minute numeric(10,2) NULL,
    peak_messages int NOT NULL DEFAULT 0, peak_bucket_minute timestamp NULL,
    new_chatters int NOT NULL DEFAULT 0, returning_chatters int NOT NULL DEFAULT 0,
    computed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS creator_chatter_stats (
    creator_id int NOT NULL, chatter_id int NOT NULL, streams_attended int NOT NULL,
    total_messages bigint NOT NULL, first_seen_stream_id int NULL, first_seen_at timestamp NULL,
    last_seen_stream_id int NULL, last_seen_at timestamp NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT creator_chatter_stats_pk PRIMARY KEY (creator_id, chatter_id)
);
"""


def _purge(cur, creator_id):
    """Delete every row this test owns, FK-safe order. No-op when creator_id is None."""
    if creator_id is None:
        return
    cur.execute("SELECT id FROM stream WHERE creator_id = %s", (creator_id,))
    stream_ids = [r[0] for r in cur.fetchall()]
    if stream_ids:
        cur.execute("DELETE FROM stream_metrics WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM stream_chatter_stats WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM stream_time_bucket WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM message WHERE stream_id = ANY(%s)", (stream_ids,))
    cur.execute("DELETE FROM creator_chatter_stats WHERE creator_id = %s", (creator_id,))
    cur.execute("DELETE FROM stream WHERE creator_id = %s", (creator_id,))
    cur.execute("DELETE FROM message_text WHERE text = %s", (MSG_TEXT,))
    cur.execute(
        "DELETE FROM chatter WHERE nick IN %s",
        (("itest_alice", "itest_bob", "itest_carol"),),
    )
    cur.execute("DELETE FROM creator WHERE id = %s", (creator_id,))


def _insert_chatter(cur, nick):
    cur.execute(
        "INSERT INTO chatter (nick) VALUES (%s) ON CONFLICT (nick) DO UPDATE SET nick = EXCLUDED.nick "
        "RETURNING id",
        (nick,),
    )
    return cur.fetchone()[0]


def _insert_messages(cur, stream_id, text_id, rows):
    for chatter_id, ts in rows:
        cur.execute(
            "INSERT INTO message (chatter_id, stream_id, message_text_id, time) VALUES (%s, %s, %s, %s)",
            (chatter_id, stream_id, text_id, ts),
        )


def _snapshot(cur, creator_id, stream_ids):
    """Deterministic snapshot of all rollup rows for the fixture's streams/creator."""
    cur.execute(
        "SELECT stream_id, bucket_minute, message_count, unique_chatters FROM stream_time_bucket "
        "WHERE stream_id = ANY(%s) ORDER BY stream_id, bucket_minute",
        (stream_ids,),
    )
    buckets = cur.fetchall()
    cur.execute(
        "SELECT stream_id, chatter_id, message_count, first_message_time, last_message_time "
        "FROM stream_chatter_stats WHERE stream_id = ANY(%s) ORDER BY stream_id, chatter_id",
        (stream_ids,),
    )
    chatter_stats = cur.fetchall()
    cur.execute(
        "SELECT stream_id, total_messages, unique_chatters, duration_seconds, messages_per_minute, "
        "peak_messages, peak_bucket_minute, new_chatters, returning_chatters "
        "FROM stream_metrics WHERE stream_id = ANY(%s) ORDER BY stream_id",
        (stream_ids,),
    )
    metrics = cur.fetchall()
    cur.execute(
        "SELECT creator_id, chatter_id, streams_attended, total_messages, first_seen_stream_id, "
        "first_seen_at, last_seen_stream_id, last_seen_at "
        "FROM creator_chatter_stats WHERE creator_id = %s ORDER BY chatter_id",
        (creator_id,),
    )
    creator_stats = cur.fetchall()
    return {"buckets": buckets, "chatter_stats": chatter_stats, "metrics": metrics, "creator_stats": creator_stats}


class TestRollupEngine:
    @pytest.fixture
    def seeded(self, test_db_connection):
        from stream_sniper.analytics.rollup_engine import compute_stream_rollup

        cur = test_db_connection.cursor()
        cur.execute(_ANALYTICS_DDL)

        # start clean (in case a prior run aborted before teardown)
        cur.execute("SELECT id FROM creator WHERE nick = %s", (CREATOR_NICK,))
        prior = cur.fetchone()
        _purge(cur, prior[0] if prior else None)

        cur.execute(
            "INSERT INTO creator (nick, display_name, profile_image_url, twitch_id) "
            "VALUES (%s, %s, %s, %s) RETURNING id",
            (CREATOR_NICK, "ITest Rollup Creator", "https://example.com/p.jpg", "999000111"),
        )
        creator_id = cur.fetchone()[0]

        cur.execute("INSERT INTO message_text (text) VALUES (%s) RETURNING id", (MSG_TEXT,))
        text_id = cur.fetchone()[0]

        alice = _insert_chatter(cur, "itest_alice")
        bob = _insert_chatter(cur, "itest_bob")
        carol = _insert_chatter(cur, "itest_carol")

        day1 = datetime(2026, 1, 1, 20, 0, 0)
        day2 = datetime(2026, 1, 2, 20, 0, 0)

        cur.execute(
            'INSERT INTO stream (twitch_id, title, start, "end", message_count, creator_id) '
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (900000001, "Stream A", day1, day1 + timedelta(hours=3), 5, creator_id),
        )
        stream_a = cur.fetchone()[0]
        cur.execute(
            'INSERT INTO stream (twitch_id, title, start, "end", message_count, creator_id) '
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (900000002, "Stream B", day2, day2 + timedelta(hours=3), 3, creator_id),
        )
        stream_b = cur.fetchone()[0]

        # Stream A: alice x3 (buckets :00,:00,:01), bob x2 (:00,:02) -> unique 2, both new
        _insert_messages(
            cur,
            stream_a,
            text_id,
            [
                (alice, day1 + timedelta(seconds=10)),
                (alice, day1 + timedelta(seconds=20)),
                (alice, day1 + timedelta(minutes=1, seconds=5)),
                (bob, day1 + timedelta(seconds=30)),
                (bob, day1 + timedelta(minutes=2)),
            ],
        )
        # Stream B: alice x2 (returning), carol x1 (new) -> unique 2, new 1, returning 1
        _insert_messages(
            cur,
            stream_b,
            text_id,
            [
                (alice, day2 + timedelta(seconds=15)),
                (alice, day2 + timedelta(minutes=3)),
                (carol, day2 + timedelta(seconds=45)),
            ],
        )

        yield {
            "conn": test_db_connection,
            "cur": cur,
            "creator_id": creator_id,
            "streams": [stream_a, stream_b],
            "compute": compute_stream_rollup,
        }

        _purge(cur, creator_id)
        cur.close()

    def test_rollup_values_and_idempotency(self, seeded):
        cur = seeded["cur"]
        creator_id = seeded["creator_id"]
        stream_a, stream_b = seeded["streams"]
        compute = seeded["compute"]

        # Roll up chronologically (A before B) so new/returning is correct.
        compute(stream_a)
        compute(stream_b)
        first = _snapshot(cur, creator_id, [stream_a, stream_b])

        # --- value checks -------------------------------------------------
        metrics_by_stream = {row[0]: row for row in first["metrics"]}
        assert set(metrics_by_stream) == {stream_a, stream_b}

        for row in first["metrics"]:
            total, unique, _dur, _mpm, _pk, _pkmin, new, returning = row[1:]
            # new + returning == unique for every stream
            assert new + returning == unique

        a = metrics_by_stream[stream_a]
        assert a[1] == 5  # total_messages
        assert a[2] == 2  # unique_chatters
        assert a[7] == 2 and a[8] == 0  # new / returning

        b = metrics_by_stream[stream_b]
        assert b[1] == 3
        assert b[2] == 2
        assert b[7] == 1 and b[8] == 1  # 1 new (carol), 1 returning (alice)
        assert b[8] > 0  # second stream has returning chatters

        # creator_chatter_stats: alice attended both streams
        creator_by_chatter = {row[1]: row for row in first["creator_stats"]}
        assert len(creator_by_chatter) == 3
        alice_row = max(first["creator_stats"], key=lambda r: r[2])  # highest streams_attended
        assert alice_row[2] == 2  # streams_attended
        assert alice_row[3] == 5  # total_messages (3 + 2)

        # --- idempotency: re-run same data, expect identical rows ---------
        compute(stream_a)
        compute(stream_b)
        second = _snapshot(cur, creator_id, [stream_a, stream_b])

        assert second["buckets"] == first["buckets"]
        assert second["chatter_stats"] == first["chatter_stats"]
        # metrics differ only by computed_at (excluded from the snapshot) -> equal
        assert second["metrics"] == first["metrics"]
        # creator_stats differ only by updated_at (excluded) -> equal
        assert second["creator_stats"] == first["creator_stats"]
