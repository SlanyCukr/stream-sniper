"""Gateway tests for the scene copypasta rollup (migration 0009).

DB-backed (real Postgres via the session fixtures, same as the other gateway tests). The base
``db_cursor`` fixture only provisions the baseline tables, so ``copypasta_db`` self-provisions
``stream_copypasta_stats`` with CREATE ... IF NOT EXISTS and truncates it per test. Runs in CI
(and any throwaway Postgres), never on the source-less dev host.
"""

from datetime import datetime, timedelta

import pytest

from stream_sniper.database.stream_copypasta_stats_table_gateway import (
    replace_stream_copypasta_stats_db,
    select_scene_copypastas_db,
    select_stream_copypasta_source_db,
)
from tests.conftest import create_test_chatter, create_test_creator, create_test_message_text, create_test_stream

_COPYPASTA_DDL = """
SET search_path TO stream_sniper;

CREATE TABLE IF NOT EXISTS stream_copypasta_stats (
    stream_id       int    NOT NULL,
    message_text_id bigint NOT NULL,
    usage_count     int    NOT NULL,
    chatter_count   int    NOT NULL,
    first_seen      timestamp NULL,
    CONSTRAINT stream_copypasta_stats_pk PRIMARY KEY (stream_id, message_text_id)
);
"""


@pytest.fixture
def copypasta_db(db_cursor):
    db_cursor.execute(_COPYPASTA_DDL)
    db_cursor.execute("TRUNCATE stream_copypasta_stats RESTART IDENTITY CASCADE")
    db_cursor.connection.commit()
    return db_cursor


def _msg(cursor, stream_id, chatter_id, text_id, when):
    cursor.execute(
        "INSERT INTO message (chatter_id, stream_id, message_text_id, time) VALUES (%s, %s, %s, %s)",
        (chatter_id, stream_id, text_id, when),
    )


class TestStreamCopypastaSource:
    """select_stream_copypasta_source_db + replace_stream_copypasta_stats_db."""

    def test_source_applies_junk_and_bot_filters(self, copypasta_db):
        creator = create_test_creator(
            copypasta_db,
            {"nick": "c", "display_name": "C", "profile_image_url": "u", "twitch_id": "s1"},
        )
        stream = create_test_stream(copypasta_db, {"twitch_id": "st1", "title": "S", "start": datetime(2024, 1, 1)}, creator)
        u1 = create_test_chatter(copypasta_db, "u1")
        u2 = create_test_chatter(copypasta_db, "u2")
        bot = create_test_chatter(copypasta_db, "botz")
        copypasta_db.execute("UPDATE chatter SET is_bot = TRUE WHERE id = %s", (bot,))

        # Qualifies via 2 distinct chatters.
        t_pasta = create_test_message_text(copypasta_db, "this is a real copypasta yes")
        # Qualifies via >= 3 uses by one chatter.
        t_spam = create_test_message_text(copypasta_db, "kappa kappa kappa kappa kap")
        # Too short (< 20 chars) -> excluded.
        t_short = create_test_message_text(copypasta_db, "short one")
        # Command (starts '!') -> excluded even though long + repeated.
        t_cmd = create_test_message_text(copypasta_db, "!drop this longwinded command")
        # Bot-only -> excluded.
        t_bot = create_test_message_text(copypasta_db, "beep boop bot pasta here now")

        base = datetime(2024, 1, 1, 20, 0, 0)
        _msg(copypasta_db, stream, u1, t_pasta, base)
        _msg(copypasta_db, stream, u2, t_pasta, base + timedelta(minutes=1))
        _msg(copypasta_db, stream, u1, t_spam, base)
        _msg(copypasta_db, stream, u1, t_spam, base + timedelta(seconds=10))
        _msg(copypasta_db, stream, u1, t_spam, base + timedelta(seconds=20))
        _msg(copypasta_db, stream, u1, t_short, base)
        _msg(copypasta_db, stream, u2, t_short, base)
        _msg(copypasta_db, stream, u1, t_cmd, base)
        _msg(copypasta_db, stream, u2, t_cmd, base)
        _msg(copypasta_db, stream, bot, t_bot, base)
        _msg(copypasta_db, stream, bot, t_bot, base + timedelta(seconds=5))
        _msg(copypasta_db, stream, bot, t_bot, base + timedelta(seconds=9))
        copypasta_db.connection.commit()

        rows = select_stream_copypasta_source_db(stream)
        by_text = {r[0]: (r[1], r[2]) for r in rows}  # message_text_id -> (usage, chatters)

        assert set(by_text) == {t_pasta, t_spam}
        assert by_text[t_pasta] == (2, 2)
        assert by_text[t_spam] == (3, 1)

    def test_replace_round_trip(self, copypasta_db):
        creator = create_test_creator(
            copypasta_db,
            {"nick": "c", "display_name": "C", "profile_image_url": "u", "twitch_id": "s1"},
        )
        stream = create_test_stream(copypasta_db, {"twitch_id": "st1", "title": "S", "start": datetime(2024, 1, 1)}, creator)
        t1 = create_test_message_text(copypasta_db, "pasta one text goes here now")
        t2 = create_test_message_text(copypasta_db, "pasta two text goes here now")

        replace_stream_copypasta_stats_db(
            stream,
            [(t1, 5, 3, datetime(2024, 1, 1, 20, 0, 0)), (t2, 9, 4, datetime(2024, 1, 1, 21, 0, 0))],
        )
        # Replacing again fully overwrites (idempotent DELETE + insert).
        replace_stream_copypasta_stats_db(stream, [(t1, 7, 2, datetime(2024, 1, 1, 20, 0, 0))])

        copypasta_db.execute(
            "SELECT message_text_id, usage_count, chatter_count FROM stream_copypasta_stats "
            "WHERE stream_id = %s ORDER BY message_text_id",
            (stream,),
        )
        rows = copypasta_db.fetchall()
        assert rows == [(t1, 7, 2)]


class TestSceneCopypastasAggregate:
    """select_scene_copypastas_db aggregates the small rollup table scene-wide."""

    @pytest.fixture
    def seeded(self, copypasta_db):
        now = datetime.now()
        c1 = create_test_creator(
            copypasta_db,
            {"nick": "c1", "display_name": "C1", "profile_image_url": "u", "twitch_id": "1"},
        )
        c2 = create_test_creator(
            copypasta_db,
            {"nick": "c2", "display_name": "C2", "profile_image_url": "u", "twitch_id": "2"},
        )
        s_recent_c1 = create_test_stream(
            copypasta_db, {"twitch_id": "r1", "title": "R1", "start": now - timedelta(days=1)}, c1
        )
        s_recent_c2 = create_test_stream(
            copypasta_db, {"twitch_id": "r2", "title": "R2", "start": now - timedelta(days=2)}, c2
        )
        s_old_c1 = create_test_stream(
            copypasta_db, {"twitch_id": "o1", "title": "O1", "start": now - timedelta(days=40)}, c1
        )
        t_wide = create_test_message_text(copypasta_db, "spreads across both channels ok")
        t_narrow = create_test_message_text(copypasta_db, "only in one single channel ok")

        # t_wide spreads across both channels; t_narrow lives only in c1's recent stream.
        replace_stream_copypasta_stats_db(
            s_recent_c1,
            [(t_wide, 10, 3, now - timedelta(days=1)), (t_narrow, 40, 6, now - timedelta(days=1))],
        )
        replace_stream_copypasta_stats_db(s_recent_c2, [(t_wide, 5, 2, now - timedelta(days=2))])
        replace_stream_copypasta_stats_db(s_old_c1, [(t_wide, 100, 9, now - timedelta(days=40))])
        copypasta_db.connection.commit()
        return {"c1": c1, "c2": c2, "t_wide": t_wide, "t_narrow": t_narrow}

    def test_all_time_usage_sort(self, seeded, copypasta_db):
        rows, total = select_scene_copypastas_db(None, None, "usage", 25, 0)
        assert total == 2
        by_text = {r[0]: r for r in rows}
        # t_wide total usage = 10 + 5 + 100 = 115 across 3 streams / 2 creators.
        wide = by_text[seeded["t_wide"]]
        assert wide[2] == 115  # usage_count
        assert wide[4] == 3  # stream_count
        assert wide[5] == 2  # creator_count
        # usage sort: t_wide (115) before t_narrow (40).
        assert rows[0][0] == seeded["t_wide"]

    def test_window_excludes_old_streams(self, seeded, copypasta_db):
        rows, total = select_scene_copypastas_db(7, None, "usage", 25, 0)
        by_text = {r[0]: r for r in rows}
        # 7-day window drops the 40-day-old stream: t_wide usage = 10 + 5 = 15, 2 streams, 2 creators.
        wide = by_text[seeded["t_wide"]]
        assert wide[2] == 15
        assert wide[4] == 2
        assert wide[5] == 2

    def test_creator_filter(self, seeded, copypasta_db):
        rows, total = select_scene_copypastas_db(None, seeded["c2"], "usage", 25, 0)
        # Only c2's recent stream has t_wide.
        assert total == 1
        assert rows[0][0] == seeded["t_wide"]
        assert rows[0][2] == 5  # only c2's usage

    def test_spread_sort_prefers_wider_reach(self, seeded, copypasta_db):
        rows, _ = select_scene_copypastas_db(None, None, "spread", 25, 0)
        # t_wide (2 creators) ranks above t_narrow (1 creator).
        assert rows[0][0] == seeded["t_wide"]
