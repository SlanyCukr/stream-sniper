from stream_sniper.database.core.connection_pool import database_entrypoint
from stream_sniper.database.core.decorators import with_cursor

@with_cursor
def q(cursor, sql):
    cursor.execute(sql)
    try:
        return cursor.fetchall()
    except Exception:
        return None

def section(title):
    print(f"\n=== {title} ===")

@database_entrypoint
def main():
    section("completed stream(s) with 0 messages - detail")
    print(q("""
        SELECT s.id, s.twitch_id, s.creator_id, s.start, s."end", s.message_count, c.nick
        FROM stream_sniper.stream s
        JOIN stream_sniper.creator c ON c.id = s.creator_id
        WHERE s."end" IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM stream_sniper.message m WHERE m.stream_id = s.id)
    """))

    section("stream 103 investigation: message_count vs actual, any duplicate message_text?")
    print(q("SELECT count(*) FROM stream_sniper.message WHERE stream_id = 103"))
    print(q("""SELECT count(*), count(distinct id) FROM stream_sniper.message WHERE stream_id = 103"""))

    section("all completed streams with message_count mismatch vs actual (full list incl completed)")
    print(q("""
        SELECT s.id, s.creator_id, s."end", s.message_count, actual.cnt, (s.message_count - actual.cnt) as diff
        FROM stream_sniper.stream s
        JOIN (SELECT stream_id, count(*) cnt FROM stream_sniper.message GROUP BY stream_id) actual
          ON actual.stream_id = s.id
        WHERE s.message_count != actual.cnt
        ORDER BY s.id
    """))

    section("creator_audience: which 15 creators have audience computed (cross check with 15 active creators)")
    print(q("""
        SELECT c.nick, ca.chatters, ca.regulars, ca.computed_at
        FROM stream_sniper.creator_audience ca
        JOIN stream_sniper.creator c ON c.id = ca.creator_id
        ORDER BY ca.chatters DESC
    """))

    section("max distinct creators a single chatter appears in (for ubiquity threshold context)")
    print(q("""
        SELECT max(cnt) FROM (
          SELECT chatter_id, count(distinct creator_id) as cnt
          FROM stream_sniper.creator_chatter_stats
          GROUP BY chatter_id
        ) x
    """))

main()
