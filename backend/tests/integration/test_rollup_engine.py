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

# The analytics rollup tables (revisions 0006-0008). Created IF NOT EXISTS so the test is
# self-provisioning against any reachable database, regardless of migration state. The
# 0008 additions (sub/emote bucket columns + emote_dictionary/stream_emote_stats) and the
# 0007 message metadata columns are required by recompute_stream_rollup_db stages (a)/(c)/(e).
_ANALYTICS_DDL = """
SET search_path TO stream_sniper;
ALTER TABLE message
    ADD COLUMN IF NOT EXISTS is_subscriber boolean  NULL,
    ADD COLUMN IF NOT EXISTS badges        text     NULL,
    ADD COLUMN IF NOT EXISTS emote_count   smallint NULL;
CREATE TABLE IF NOT EXISTS stream_time_bucket (
    stream_id int NOT NULL, bucket_minute timestamp NOT NULL,
    message_count int NOT NULL, unique_chatters int NOT NULL,
    sub_messages int NULL, emote_messages int NULL,
    CONSTRAINT stream_time_bucket_pk PRIMARY KEY (stream_id, bucket_minute)
);
ALTER TABLE stream_time_bucket
    ADD COLUMN IF NOT EXISTS sub_messages int NULL,
    ADD COLUMN IF NOT EXISTS emote_messages int NULL;
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
    sub_messages int NULL, emote_messages int NULL,
    computed_at timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE stream_metrics
    ADD COLUMN IF NOT EXISTS sub_messages int NULL,
    ADD COLUMN IF NOT EXISTS emote_messages int NULL;
CREATE TABLE IF NOT EXISTS creator_chatter_stats (
    creator_id int NOT NULL, chatter_id int NOT NULL, streams_attended int NOT NULL,
    total_messages bigint NOT NULL, first_seen_stream_id int NULL, first_seen_at timestamp NULL,
    last_seen_stream_id int NULL, last_seen_at timestamp NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT creator_chatter_stats_pk PRIMARY KEY (creator_id, chatter_id)
);
CREATE TABLE IF NOT EXISTS emote_dictionary (
    id serial PRIMARY KEY, name text NOT NULL,
    source text NOT NULL CHECK (source IN ('bttv','twitch')),
    provider_id text NULL, first_seen timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT emote_dictionary_uq UNIQUE (name, source)
);
CREATE TABLE IF NOT EXISTS stream_emote_stats (
    stream_id int NOT NULL, emote_id int NOT NULL,
    usage_count int NOT NULL, chatter_count int NOT NULL,
    CONSTRAINT stream_emote_stats_pk PRIMARY KEY (stream_id, emote_id)
);
CREATE TABLE IF NOT EXISTS stream_phrase_stats (
    stream_id int NOT NULL, phrase text NOT NULL,
    usage_count int NOT NULL, chatter_count int NOT NULL,
    CONSTRAINT stream_phrase_stats_pk PRIMARY KEY (stream_id, phrase)
);
CREATE TABLE IF NOT EXISTS stream_moment (
    stream_id int NOT NULL, bucket_minute timestamp NOT NULL,
    offset_seconds int NOT NULL, message_count int NOT NULL,
    baseline numeric(10,2) NOT NULL, ratio numeric(10,2) NULL, unique_chatters int NOT NULL,
    sub_share numeric(5,4) NULL, emote_share numeric(5,4) NULL,
    top_phrases jsonb NULL, sample_messages jsonb NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT stream_moment_pk PRIMARY KEY (stream_id, bucket_minute)
);
CREATE TABLE IF NOT EXISTS moment_review (
    stream_id int NOT NULL, bucket_minute timestamp NOT NULL,
    status text NOT NULL, updated_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT moment_review_pk PRIMARY KEY (stream_id, bucket_minute)
);
CREATE TABLE IF NOT EXISTS creator_audience (
    creator_id int PRIMARY KEY, chatters int NOT NULL, regulars int NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS creator_overlap (
    creator_a int NOT NULL, creator_b int NOT NULL,
    shared_chatters int NOT NULL, shared_regulars int NOT NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT creator_overlap_pk PRIMARY KEY (creator_a, creator_b)
);
"""


def _purge(cur, creator_id):
    """Delete every row this test owns, FK-safe order. No-op when creator_id is None."""
    if creator_id is None:
        return
    cur.execute("SELECT id FROM stream WHERE creator_id = %s", (creator_id,))
    stream_ids = [r[0] for r in cur.fetchall()]
    if stream_ids:
        cur.execute("DELETE FROM moment_review WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM stream_moment WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM stream_phrase_stats WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM stream_emote_stats WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM stream_metrics WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM stream_chatter_stats WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM stream_time_bucket WHERE stream_id = ANY(%s)", (stream_ids,))
        cur.execute("DELETE FROM message WHERE stream_id = ANY(%s)", (stream_ids,))
    cur.execute(
        "DELETE FROM creator_overlap WHERE creator_a = %s OR creator_b = %s", (creator_id, creator_id)
    )
    cur.execute("DELETE FROM creator_audience WHERE creator_id = %s", (creator_id,))
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


def _insert_text(cur, text):
    cur.execute(
        "INSERT INTO message_text (text) VALUES (%s) ON CONFLICT (text) DO UPDATE SET text = EXCLUDED.text "
        "RETURNING id",
        (text,),
    )
    return cur.fetchone()[0]


def _insert_creator(cur, nick):
    cur.execute(
        "INSERT INTO creator (nick, display_name, profile_image_url, twitch_id) "
        "VALUES (%s, %s, %s, %s) RETURNING id",
        (nick, nick, "https://example.com/p.jpg", None),
    )
    return cur.fetchone()[0]


class TestAnalyticsExpansionRollup:
    """Emote / phrase / moment rollups + community overlap correctness (revisions 0006-0008)."""

    _ENRICH_CREATOR = "itest_enrich_creator"
    _ENRICH_CHATTERS = ["itest_e1", "itest_e2", "itest_e3", "itest_e4", "itest_e5"]
    _T_LOW = "itest_enrich_hello"
    _T_SPIKE = "OMEGALUL insane play"  # OMEGALUL is a seeded BTTV emote

    @pytest.fixture
    def enrich_seeded(self, test_db_connection):
        from stream_sniper.analytics.rollup_engine import compute_stream_rollup

        cur = test_db_connection.cursor()
        cur.execute(_ANALYTICS_DDL)

        cur.execute("SELECT id FROM creator WHERE nick = %s", (self._ENRICH_CREATOR,))
        prior = cur.fetchone()
        self._cleanup(cur, prior[0] if prior else None)

        creator_id = _insert_creator(cur, self._ENRICH_CREATOR)
        chatter_ids = [_insert_chatter(cur, nick) for nick in self._ENRICH_CHATTERS]
        low_id = _insert_text(cur, self._T_LOW)
        spike_id = _insert_text(cur, self._T_SPIKE)

        # Guarantee the emote is present regardless of whether the lazy BTTV seed ran (it skips
        # when the shared DB already has any bttv row from another test) — the assertion targets
        # emote text-matching, not the one-time seed.
        cur.execute(
            "INSERT INTO emote_dictionary (name, source, provider_id) "
            "VALUES ('OMEGALUL','bttv','60ca186ef8b3f62601c3eb1d') ON CONFLICT (name, source) DO NOTHING"
        )

        day = datetime(2026, 3, 1, 18, 0, 0)
        cur.execute(
            'INSERT INTO stream (twitch_id, title, start, "end", message_count, creator_id) '
            "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (910000001, "Enrich Stream", day, day + timedelta(hours=3), 0, creator_id),
        )
        stream_id = cur.fetchone()[0]

        # Low baseline minutes 0-9 and 11-12 (2 msgs each), spike at minute 10 (20 msgs, 5 chatters).
        for minute in list(range(10)) + [11, 12]:
            for i in range(2):
                cur.execute(
                    "INSERT INTO message (chatter_id, stream_id, message_text_id, time) VALUES (%s,%s,%s,%s)",
                    (chatter_ids[i], stream_id, low_id, day + timedelta(minutes=minute, seconds=5 * i)),
                )
        for i in range(20):
            cur.execute(
                "INSERT INTO message (chatter_id, stream_id, message_text_id, time) VALUES (%s,%s,%s,%s)",
                (chatter_ids[i % 5], stream_id, spike_id, day + timedelta(minutes=10, seconds=i)),
            )

        yield {"cur": cur, "creator_id": creator_id, "stream_id": stream_id, "compute": compute_stream_rollup}

        self._cleanup(cur, creator_id)
        cur.close()

    def _cleanup(self, cur, creator_id):
        if creator_id is not None:
            cur.execute("SELECT id FROM stream WHERE creator_id = %s", (creator_id,))
            stream_ids = [r[0] for r in cur.fetchall()]
            if stream_ids:
                for table in (
                    "moment_review",
                    "stream_moment",
                    "stream_phrase_stats",
                    "stream_emote_stats",
                    "stream_metrics",
                    "stream_chatter_stats",
                    "stream_time_bucket",
                    "message",
                ):
                    cur.execute(f"DELETE FROM {table} WHERE stream_id = ANY(%s)", (stream_ids,))
            cur.execute(
                "DELETE FROM creator_overlap WHERE creator_a = %s OR creator_b = %s", (creator_id, creator_id)
            )
            cur.execute("DELETE FROM creator_audience WHERE creator_id = %s", (creator_id,))
            cur.execute("DELETE FROM creator_chatter_stats WHERE creator_id = %s", (creator_id,))
            cur.execute("DELETE FROM stream WHERE creator_id = %s", (creator_id,))
            cur.execute("DELETE FROM creator WHERE id = %s", (creator_id,))
        cur.execute("DELETE FROM message_text WHERE text IN %s", ((self._T_LOW, self._T_SPIKE),))
        cur.execute("DELETE FROM chatter WHERE nick = ANY(%s)", (self._ENRICH_CHATTERS,))

    def test_emote_phrase_and_moment_rows(self, enrich_seeded):
        cur = enrich_seeded["cur"]
        stream_id = enrich_seeded["stream_id"]
        enrich_seeded["compute"](stream_id)

        # emote rollup: OMEGALUL matched via the seeded BTTV dictionary, 20 uses by 5 chatters.
        cur.execute(
            """
            SELECT ed.name, ses.usage_count, ses.chatter_count
            FROM stream_emote_stats ses
            JOIN emote_dictionary ed ON ed.id = ses.emote_id
            WHERE ses.stream_id = %s AND ed.name = 'OMEGALUL'
            """,
            (stream_id,),
        )
        emote = cur.fetchone()
        assert emote == ("OMEGALUL", 20, 5)

        # phrase rollup: "insane play" bigram present; the emote token is NOT a phrase.
        cur.execute(
            "SELECT phrase, usage_count, chatter_count FROM stream_phrase_stats WHERE stream_id = %s",
            (stream_id,),
        )
        phrases = {row[0]: (row[1], row[2]) for row in cur.fetchall()}
        assert phrases["insane play"] == (20, 5)
        assert "omegalul" not in phrases and "OMEGALUL" not in phrases

        # moment rollup: one enriched spike at minute 10.
        cur.execute(
            """
            SELECT message_count, sub_share, emote_share, top_phrases, sample_messages
            FROM stream_moment WHERE stream_id = %s
            """,
            (stream_id,),
        )
        moments = cur.fetchall()
        assert len(moments) == 1
        message_count, sub_share, emote_share, top_phrases, sample_messages = moments[0]
        assert message_count == 20
        assert float(sub_share) == 0.0 and float(emote_share) == 0.0
        assert any(p["phrase"] == "insane play" for p in top_phrases)
        assert sample_messages[0] == {"text": self._T_SPIKE, "count": 20}

    def test_three_creator_overlap_correctness(self, test_db_connection):
        from stream_sniper.analytics.community import recompute_creator_overlap

        cur = test_db_connection.cursor()
        cur.execute(_ANALYTICS_DDL)
        nicks = ["itest_ov_x", "itest_ov_y", "itest_ov_z"]
        chatter_nicks = ["itest_ovc1", "itest_ovc2", "itest_ovc3"]

        for nick in nicks:
            cur.execute("SELECT id FROM creator WHERE nick = %s", (nick,))
            row = cur.fetchone()
            if row:
                cur.execute(
                    "DELETE FROM creator_overlap WHERE creator_a = %s OR creator_b = %s", (row[0], row[0])
                )
                cur.execute("DELETE FROM creator_audience WHERE creator_id = %s", (row[0],))
                cur.execute("DELETE FROM creator_chatter_stats WHERE creator_id = %s", (row[0],))
                cur.execute("DELETE FROM creator WHERE id = %s", (row[0],))
        cur.execute("DELETE FROM chatter WHERE nick = ANY(%s)", (chatter_nicks,))

        try:
            cx, cy, cz = (_insert_creator(cur, nick) for nick in nicks)
            ch1, ch2, ch3 = (_insert_chatter(cur, nick) for nick in chatter_nicks)

            # ch1: regular in X and Y; ch2: casual in X and Y; ch3: casual in X and Z.
            rows = [
                (cx, ch1, 5), (cy, ch1, 4),
                (cx, ch2, 1), (cy, ch2, 1),
                (cx, ch3, 2), (cz, ch3, 2),
            ]
            for creator_id, chatter_id, attended in rows:
                cur.execute(
                    "INSERT INTO creator_chatter_stats "
                    "(creator_id, chatter_id, streams_attended, total_messages) VALUES (%s,%s,%s,%s)",
                    (creator_id, chatter_id, attended, attended * 10),
                )

            assert recompute_creator_overlap(blocking=True) is True

            ids = [cx, cy, cz]
            cur.execute(
                "SELECT creator_a, creator_b, shared_chatters, shared_regulars FROM creator_overlap "
                "WHERE creator_a = ANY(%s) AND creator_b = ANY(%s)",
                (ids, ids),
            )
            overlap = {frozenset((a, b)): (sc, sr) for a, b, sc, sr in cur.fetchall()}
            assert overlap[frozenset((cx, cy))] == (2, 1)  # ch1+ch2 shared, only ch1 regular in both
            assert overlap[frozenset((cx, cz))] == (1, 0)  # ch3 shared, not regular
            assert frozenset((cy, cz)) not in overlap  # no shared chatters

            cur.execute(
                "SELECT creator_id, chatters, regulars FROM creator_audience WHERE creator_id = ANY(%s)",
                (ids,),
            )
            audience = {cid: (ch, reg) for cid, ch, reg in cur.fetchall()}
            assert audience[cx] == (3, 1)
            assert audience[cy] == (2, 1)
            assert audience[cz] == (1, 0)
        finally:
            for cid in (cx, cy, cz):
                cur.execute("DELETE FROM creator_overlap WHERE creator_a = %s OR creator_b = %s", (cid, cid))
                cur.execute("DELETE FROM creator_audience WHERE creator_id = %s", (cid,))
                cur.execute("DELETE FROM creator_chatter_stats WHERE creator_id = %s", (cid,))
            cur.execute("DELETE FROM creator WHERE nick = ANY(%s)", (nicks,))
            cur.execute("DELETE FROM chatter WHERE nick = ANY(%s)", (chatter_nicks,))
            cur.close()

    def test_same_name_in_both_sources_counts_once(self, test_db_connection):
        from stream_sniper.analytics.rollup_engine import compute_stream_rollup

        cur = test_db_connection.cursor()
        cur.execute(_ANALYTICS_DDL)
        creator_nick = "itest_dup_creator"
        chatter_nicks = ["itest_dup1", "itest_dup2"]
        emote_name = "ITESTDUPEMOTE"  # not in the BTTV seed

        cur.execute("SELECT id FROM creator WHERE nick = %s", (creator_nick,))
        prior = cur.fetchone()
        if prior:
            cur.execute("SELECT id FROM stream WHERE creator_id = %s", (prior[0],))
            for (sid,) in cur.fetchall():
                cur.execute("DELETE FROM stream_emote_stats WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM message WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM stream WHERE id = %s", (sid,))
            cur.execute("DELETE FROM creator WHERE id = %s", (prior[0],))
        cur.execute("DELETE FROM chatter WHERE nick = ANY(%s)", (chatter_nicks,))
        cur.execute("DELETE FROM emote_dictionary WHERE name = %s", (emote_name,))

        try:
            creator_id = _insert_creator(cur, creator_nick)
            c1, c2 = (_insert_chatter(cur, nick) for nick in chatter_nicks)
            text_id = _insert_text(cur, emote_name)

            # Same name in both sources; twitch must win the DISTINCT ON dedup.
            cur.execute(
                "INSERT INTO emote_dictionary (name, source, provider_id) VALUES (%s,'bttv',%s) RETURNING id",
                (emote_name, "abc123abc123"),
            )
            bttv_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO emote_dictionary (name, source, provider_id) VALUES (%s,'twitch',%s) RETURNING id",
                (emote_name, "555"),
            )
            twitch_id = cur.fetchone()[0]

            day = datetime(2026, 4, 1, 12, 0, 0)
            cur.execute(
                'INSERT INTO stream (twitch_id, title, start, "end", message_count, creator_id) '
                "VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
                (920000001, "Dup Stream", day, day + timedelta(hours=1), 0, creator_id),
            )
            stream_id = cur.fetchone()[0]
            for i, chatter_id in enumerate((c1, c1, c2)):
                cur.execute(
                    "INSERT INTO message (chatter_id, stream_id, message_text_id, time) VALUES (%s,%s,%s,%s)",
                    (chatter_id, stream_id, text_id, day + timedelta(seconds=i)),
                )

            compute_stream_rollup(stream_id)

            cur.execute(
                "SELECT emote_id, usage_count, chatter_count FROM stream_emote_stats WHERE stream_id = %s",
                (stream_id,),
            )
            emote_rows = cur.fetchall()
            assert len(emote_rows) == 1  # deduped to a single emote despite two dictionary sources
            emote_id, usage_count, chatter_count = emote_rows[0]
            assert emote_id == twitch_id and emote_id != bttv_id  # twitch priority
            assert usage_count == 3 and chatter_count == 2
        finally:
            cur.execute("SELECT id FROM stream WHERE creator_id = %s", (creator_id,))
            for (sid,) in cur.fetchall():
                cur.execute("DELETE FROM stream_emote_stats WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM stream_phrase_stats WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM stream_moment WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM stream_metrics WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM stream_chatter_stats WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM stream_time_bucket WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM message WHERE stream_id = %s", (sid,))
                cur.execute("DELETE FROM stream WHERE id = %s", (sid,))
            cur.execute("DELETE FROM creator_overlap WHERE creator_a = %s OR creator_b = %s", (creator_id, creator_id))
            cur.execute("DELETE FROM creator_audience WHERE creator_id = %s", (creator_id,))
            cur.execute("DELETE FROM creator_chatter_stats WHERE creator_id = %s", (creator_id,))
            cur.execute("DELETE FROM creator WHERE id = %s", (creator_id,))
            cur.execute("DELETE FROM chatter WHERE nick = ANY(%s)", (chatter_nicks,))
            cur.execute("DELETE FROM emote_dictionary WHERE name = %s", (emote_name,))
            cur.execute("DELETE FROM message_text WHERE text = %s", (emote_name,))
            cur.close()
