"""Gateway tests for the analytics-expansion tables (migration 0008).

DB-backed (real Postgres via the session ``test_db_connection`` fixture, same as the other
gateway tests). The base ``db_cursor`` fixture only provisions/cleans the baseline tables,
so ``analytics_db`` here self-provisions the 0006+0008 analytics tables (and the 0007
message metadata columns) with CREATE ... IF NOT EXISTS and truncates them per test.
"""

from datetime import datetime, timedelta

import pytest

from stream_sniper.database.creator_overlap_table_gateway import (
    recompute_creator_overlap_db,
    select_creator_neighbors_db,
    select_overlap_db,
)
from stream_sniper.database.emote_dictionary_table_gateway import (
    seed_emote_dictionary_db,
    select_dictionary_count_db,
    upsert_twitch_emotes_db,
)
from stream_sniper.database.moment_review_table_gateway import (
    delete_moment_review_db,
    upsert_moment_review_db,
)
from stream_sniper.database.stream_chatter_stats_table_gateway import recompute_stream_rollup_db
from stream_sniper.database.stream_emote_stats_table_gateway import (
    select_creator_emotes_db,
    select_stream_emotes_db,
)
from stream_sniper.database.stream_metrics_table_gateway import select_stream_metrics_db
from stream_sniper.database.stream_moment_table_gateway import (
    replace_stream_text_rollups_db,
    select_stream_moments_db,
)
from stream_sniper.database.stream_phrase_stats_table_gateway import select_stream_phrases_db
from stream_sniper.database.stream_time_bucket_table_gateway import select_stream_buckets_db
from tests.conftest import create_test_chatter, create_test_creator, create_test_message_text, create_test_stream

_EXPANSION_DDL = """
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
    stream_id int NOT NULL, bucket_minute timestamp NOT NULL, offset_seconds int NOT NULL,
    message_count int NOT NULL, baseline numeric(10,2) NOT NULL, ratio numeric(10,2) NULL,
    unique_chatters int NOT NULL, sub_share numeric(5,4) NULL, emote_share numeric(5,4) NULL,
    top_phrases jsonb NULL, sample_messages jsonb NULL,
    computed_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT stream_moment_pk PRIMARY KEY (stream_id, bucket_minute)
);
CREATE TABLE IF NOT EXISTS moment_review (
    stream_id int NOT NULL, bucket_minute timestamp NOT NULL,
    status text NOT NULL CHECK (status IN ('bookmarked','rejected')),
    updated_at timestamptz NOT NULL DEFAULT now(),
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
    CONSTRAINT creator_overlap_pk PRIMARY KEY (creator_a, creator_b),
    CONSTRAINT creator_overlap_order_ck CHECK (creator_a < creator_b)
);
"""

_ANALYTICS_TABLES = [
    "creator_overlap",
    "creator_audience",
    "moment_review",
    "stream_moment",
    "stream_phrase_stats",
    "stream_emote_stats",
    "emote_dictionary",
    "creator_chatter_stats",
    "stream_metrics",
    "stream_chatter_stats",
    "stream_time_bucket",
]


@pytest.fixture
def analytics_db(db_cursor):
    db_cursor.execute(_EXPANSION_DDL)
    db_cursor.execute(f"TRUNCATE {', '.join(_ANALYTICS_TABLES)} RESTART IDENTITY CASCADE")
    db_cursor.connection.commit()
    return db_cursor


def _emote_id(cursor, name, source):
    cursor.execute("SELECT id FROM emote_dictionary WHERE name = %s AND source = %s", (name, source))
    return cursor.fetchone()[0]


def _add_ccs(cursor, creator_id, chatter_id, streams_attended, total_messages=1):
    cursor.execute(
        "INSERT INTO creator_chatter_stats (creator_id, chatter_id, streams_attended, total_messages) "
        "VALUES (%s, %s, %s, %s)",
        (creator_id, chatter_id, streams_attended, total_messages),
    )


class TestEmoteDictionaryGateway:
    def test_seed_and_count(self, analytics_db):
        seed_emote_dictionary_db(
            [("KEKW", "bttv", "5f9b1a2c3d4e5f6a7b8c9d0e"), ("Pog", "bttv", "aaaaaaaaaaaa")]
        )
        assert select_dictionary_count_db("bttv") == 2
        assert select_dictionary_count_db("twitch") == 0

    def test_seed_is_idempotent_on_name_source(self, analytics_db):
        seed_emote_dictionary_db([("KEKW", "bttv", "abc123abc123")])
        seed_emote_dictionary_db([("KEKW", "bttv", "different000000")])
        assert select_dictionary_count_db("bttv") == 1

    def test_twitch_upsert_validates_provider_id(self, analytics_db):
        # First id is a valid twitch id; second contains a '/' (URL-path injection) -> NULL.
        upsert_twitch_emotes_db([("KEKW", "301234"), ("Evil", "../../etc/passwd")])
        analytics_db.execute(
            "SELECT name, provider_id FROM emote_dictionary WHERE source = 'twitch' ORDER BY name"
        )
        rows = dict(analytics_db.fetchall())
        assert rows["KEKW"] == "301234"
        assert rows["Evil"] is None

    def test_twitch_upsert_empty_is_noop(self, analytics_db):
        upsert_twitch_emotes_db([])
        assert select_dictionary_count_db("twitch") == 0


class TestStreamEmoteStatsGateway:
    def test_select_stream_and_creator_emotes(self, analytics_db):
        creator_id = create_test_creator(analytics_db)
        s1 = create_test_stream(analytics_db, {"twitch_id": "s1", "title": "s1"}, creator_id)
        s2 = create_test_stream(analytics_db, {"twitch_id": "s2", "title": "s2"}, creator_id)
        seed_emote_dictionary_db([("KEKW", "bttv", "aaaaaaaaaaaa"), ("Pog", "twitch", "301")])
        kekw = _emote_id(analytics_db, "KEKW", "bttv")
        pog = _emote_id(analytics_db, "Pog", "twitch")
        analytics_db.execute(
            "INSERT INTO stream_emote_stats (stream_id, emote_id, usage_count, chatter_count) "
            "VALUES (%s,%s,%s,%s),(%s,%s,%s,%s),(%s,%s,%s,%s)",
            (s1, kekw, 10, 4, s1, pog, 3, 2, s2, kekw, 5, 3),
        )
        analytics_db.connection.commit()

        stream_rows = select_stream_emotes_db(s1, 25)
        assert stream_rows[0][0] == "KEKW"  # ordered usage DESC
        assert stream_rows[0][3] == 10 and stream_rows[0][4] == 4
        assert stream_rows[1][0] == "Pog"

        creator_rows = select_creator_emotes_db(creator_id, 25)
        by_name = {r[0]: r for r in creator_rows}
        # KEKW summed across s1+s2: usage 15, chatters 7, in 2 streams.
        assert by_name["KEKW"][3] == 15
        assert by_name["KEKW"][4] == 7
        assert by_name["KEKW"][5] == 2
        assert by_name["Pog"][5] == 1


class TestStreamTextRollups:
    def test_replace_writes_phrases_and_moments_atomically(self, analytics_db):
        creator_id = create_test_creator(analytics_db)
        stream_id = create_test_stream(analytics_db, {"twitch_id": "s1", "title": "s1"}, creator_id)
        bucket = datetime(2026, 1, 1, 20, 5, 0)
        phrases = [("lol", 12, 5), ("no way", 6, 4)]
        moments = [
            (bucket, 300, 90, 6.0, 15.0, 30, 0.25, 0.5,
             [{"phrase": "lol", "count": 12, "lift": 3.0}],
             [{"text": "lol", "count": 8}]),
        ]
        replace_stream_text_rollups_db(stream_id, phrases, moments)

        prows = select_stream_phrases_db(stream_id, 25)
        assert prows[0] == ("lol", 12, 5)

        mrows = select_stream_moments_db(stream_id)
        assert len(mrows) == 1
        m = mrows[0]
        assert m[0] == "2026-01-01T20:05:00"  # bucket_minute
        assert m[4] == 15.0  # ratio double precision
        assert m[8] == [{"phrase": "lol", "count": 12, "lift": 3.0}]  # jsonb top_phrases
        assert m[9] == [{"text": "lol", "count": 8}]  # jsonb sample_messages
        assert m[10] is None  # no review yet

    def test_replace_is_idempotent(self, analytics_db):
        creator_id = create_test_creator(analytics_db)
        stream_id = create_test_stream(analytics_db, {"twitch_id": "s1", "title": "s1"}, creator_id)
        b = datetime(2026, 1, 1, 20, 5, 0)
        replace_stream_text_rollups_db(
            stream_id, [("a", 3, 2)], [(b, 0, 20, 2.0, 10.0, 5, None, None, None, None)]
        )
        replace_stream_text_rollups_db(
            stream_id, [("b", 4, 3)], [(b, 0, 20, 2.0, 10.0, 5, None, None, None, None)]
        )
        prows = select_stream_phrases_db(stream_id, 25)
        assert [r[0] for r in prows] == ["b"]  # prior phrase "a" replaced
        assert len(select_stream_moments_db(stream_id)) == 1


class TestMomentReviewGateway:
    def test_upsert_delete_roundtrip(self, analytics_db):
        creator_id = create_test_creator(analytics_db)
        stream_id = create_test_stream(analytics_db, {"twitch_id": "s1", "title": "s1"}, creator_id)
        b = datetime(2026, 1, 1, 20, 5, 0)
        replace_stream_text_rollups_db(
            stream_id, [], [(b, 0, 20, 2.0, 10.0, 5, None, None, None, None)]
        )

        updated_at = upsert_moment_review_db(stream_id, b, "bookmarked")
        assert isinstance(updated_at, str) and updated_at.startswith("2026-")
        assert select_stream_moments_db(stream_id)[0][10] == "bookmarked"

        upsert_moment_review_db(stream_id, b, "rejected")
        assert select_stream_moments_db(stream_id)[0][10] == "rejected"

        assert delete_moment_review_db(stream_id, b) == 1
        assert select_stream_moments_db(stream_id)[0][10] is None
        assert delete_moment_review_db(stream_id, b) == 0


class TestCreatorOverlapGateway:
    @pytest.fixture
    def overlap_seed(self, analytics_db):
        c1 = create_test_creator(
            analytics_db,
            {"nick": "c1", "display_name": "C One", "profile_image_url": "u", "twitch_id": "1"},
        )
        c2 = create_test_creator(
            analytics_db,
            {"nick": "c2", "display_name": "C Two", "profile_image_url": "u", "twitch_id": "2"},
        )
        c3 = create_test_creator(
            analytics_db,
            {"nick": "c3", "display_name": "C Three", "profile_image_url": "u", "twitch_id": "3"},
        )
        cha = create_test_chatter(analytics_db, "chA")
        chb = create_test_chatter(analytics_db, "chB")
        chc = create_test_chatter(analytics_db, "chC")
        _add_ccs(analytics_db, c1, cha, 4)
        _add_ccs(analytics_db, c1, chb, 2)
        _add_ccs(analytics_db, c1, chc, 5)
        _add_ccs(analytics_db, c2, cha, 3)
        _add_ccs(analytics_db, c2, chb, 1)
        _add_ccs(analytics_db, c3, chc, 2)
        analytics_db.connection.commit()
        return {"c1": c1, "c2": c2, "c3": c3}

    def test_recompute_audience_and_overlap(self, overlap_seed, analytics_db):
        assert recompute_creator_overlap_db(True) is True
        c1, c2, c3 = overlap_seed["c1"], overlap_seed["c2"], overlap_seed["c3"]

        analytics_db.execute("SELECT creator_id, chatters, regulars FROM creator_audience ORDER BY creator_id")
        aud = {r[0]: (r[1], r[2]) for r in analytics_db.fetchall()}
        assert aud[c1] == (3, 2)
        assert aud[c2] == (2, 1)
        assert aud[c3] == (1, 0)

        analytics_db.execute(
            "SELECT creator_a, creator_b, shared_chatters, shared_regulars FROM creator_overlap "
            "ORDER BY creator_a, creator_b"
        )
        pairs = {(r[0], r[1]): (r[2], r[3]) for r in analytics_db.fetchall()}
        assert pairs[(c1, c2)] == (2, 1)
        assert pairs[(c1, c3)] == (1, 0)
        assert (c2, c3) not in pairs  # no shared chatters

    def test_recompute_is_idempotent(self, overlap_seed, analytics_db):
        recompute_creator_overlap_db(True)
        recompute_creator_overlap_db(True)
        analytics_db.execute("SELECT count(*) FROM creator_overlap")
        assert analytics_db.fetchone()[0] == 2

    def test_select_overlap_top_n(self, overlap_seed, analytics_db):
        recompute_creator_overlap_db(True)
        c1, c2 = overlap_seed["c1"], overlap_seed["c2"]
        creators, pairs = select_overlap_db(2)
        assert [c[0] for c in creators] == [c1, c2]  # top 2 by chatters
        assert len(creators[0]) == 6  # incl display_name + computed_at
        # pairs restricted to the top-2 set -> only (c1, c2), c3's pair excluded.
        assert {(p[0], p[1]) for p in pairs} == {(c1, c2)}

    def test_select_neighbors_both_directions_and_metric_whitelist(self, overlap_seed, analytics_db):
        recompute_creator_overlap_db(True)
        c1, c2, c3 = overlap_seed["c1"], overlap_seed["c2"], overlap_seed["c3"]

        by_chatters = select_creator_neighbors_db(c1, "shared_chatters", 10)
        assert [r[0] for r in by_chatters] == [c2, c3]  # c2(2) before c3(1)

        # c2 only appears as creator_b in (c1,c2): both-directions read still finds c1.
        c2_neighbors = select_creator_neighbors_db(c2, "shared_chatters", 10)
        assert [r[0] for r in c2_neighbors] == [c1]

        # Unknown metric falls back to shared_chatters (whitelist), never interpolated.
        fallback = select_creator_neighbors_db(c1, "; DROP TABLE creator_overlap; --", 10)
        assert [r[0] for r in fallback] == [c2, c3]


class TestRecomputeRollupExtensions:
    def test_sub_emote_messages_and_emote_stats(self, analytics_db):
        creator_id = create_test_creator(analytics_db)
        stream_id = create_test_stream(
            analytics_db,
            {
                "twitch_id": "s1",
                "title": "s1",
                "start": datetime(2026, 1, 1, 20, 0, 0),
                "end": datetime(2026, 1, 1, 21, 0, 0),
            },
            creator_id,
        )
        alice = create_test_chatter(analytics_db, "alice")
        bob = create_test_chatter(analytics_db, "bob")
        t_emote1 = create_test_message_text(analytics_db, "hello KEKW nice")
        t_emote2 = create_test_message_text(analytics_db, "KEKW KEKW")
        t_plain = create_test_message_text(analytics_db, "just chatting")
        # Name-deduped dictionary: KEKW in BOTH sources must count once (twitch priority);
        # 'no' is < 3 chars and must be ignored; case-sensitive so 'kekw' would not match.
        seed_emote_dictionary_db([("KEKW", "bttv", "aaaaaaaaaaaa"), ("no", "twitch", "1")])
        upsert_twitch_emotes_db([("KEKW", "555"), ("Pog", "777")])

        base = datetime(2026, 1, 1, 20, 0, 0)
        rows = [
            (alice, stream_id, t_emote1, base + timedelta(seconds=5), True, 1),
            (bob, stream_id, t_emote2, base + timedelta(seconds=15), None, 2),
            (bob, stream_id, t_plain, base + timedelta(seconds=25), None, None),
        ]
        for chatter_id, sid, text_id, ts, sub, emote_count in rows:
            analytics_db.execute(
                "INSERT INTO message (chatter_id, stream_id, message_text_id, time, is_subscriber, emote_count) "
                "VALUES (%s,%s,%s,%s,%s,%s)",
                (chatter_id, sid, text_id, ts, sub, emote_count),
            )
        analytics_db.connection.commit()

        recompute_stream_rollup_db(stream_id, creator_id)

        buckets = select_stream_buckets_db(stream_id)
        assert len(buckets) == 1
        assert len(buckets[0]) == 5  # bucket, msgs, uniq, sub_messages, emote_messages
        assert buckets[0][3] == 1  # sub_messages (alice only)
        assert buckets[0][4] == 2  # emote_messages (two messages carry emote_count)

        metrics = select_stream_metrics_db(stream_id)
        assert len(metrics) == 10
        assert metrics[8] == 1  # sub_messages
        assert metrics[9] == 2  # emote_messages

        emotes = select_stream_emotes_db(stream_id, 25)
        assert len(emotes) == 1  # only KEKW; 'no' too short, 'Pog' unused
        assert emotes[0][0] == "KEKW"
        assert emotes[0][1] == "twitch"  # twitch wins the name dedup
        assert emotes[0][3] == 3  # usage 1 + 2
        assert emotes[0][4] == 2  # chatter_count alice + bob

    def test_null_metadata_stream_reports_null_sub_emote(self, analytics_db):
        # A stream whose messages predate rev 0007 carry NULL is_subscriber/emote_count. The
        # re-rollup must report NULL (unknown), never 0, for sub/emote messages at both the bucket
        # and metrics level — so the frontend can distinguish "unknown" from "known, none observed".
        creator_id = create_test_creator(analytics_db)
        stream_id = create_test_stream(
            analytics_db,
            {
                "twitch_id": "snull",
                "title": "snull",
                "start": datetime(2026, 1, 1, 20, 0, 0),
                "end": datetime(2026, 1, 1, 21, 0, 0),
            },
            creator_id,
        )
        alice = create_test_chatter(analytics_db, "alice")
        text_id = create_test_message_text(analytics_db, "just chatting")
        base = datetime(2026, 1, 1, 20, 0, 0)
        for offset in (5, 15, 25):
            analytics_db.execute(
                "INSERT INTO message (chatter_id, stream_id, message_text_id, time, is_subscriber, emote_count) "
                "VALUES (%s,%s,%s,%s,NULL,NULL)",
                (alice, stream_id, text_id, base + timedelta(seconds=offset)),
            )
        analytics_db.connection.commit()

        recompute_stream_rollup_db(stream_id, creator_id)

        buckets = select_stream_buckets_db(stream_id)
        assert len(buckets) == 1
        assert buckets[0][1] == 3  # message_count still counted
        assert buckets[0][3] is None  # sub_messages unknown (not 0)
        assert buckets[0][4] is None  # emote_messages unknown (not 0)

        metrics = select_stream_metrics_db(stream_id)
        assert metrics[0] == 3  # total_messages
        assert metrics[8] is None  # sub_messages NULL
        assert metrics[9] is None  # emote_messages NULL
