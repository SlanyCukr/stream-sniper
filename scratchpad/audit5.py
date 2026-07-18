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
    section("creator.twitch_id populated for the 22 zero-stream creators?")
    print(q("""
        SELECT c.nick, c.twitch_id
        FROM stream_sniper.creator c
        WHERE NOT EXISTS (SELECT 1 FROM stream_sniper.stream s WHERE s.creator_id = c.id)
        ORDER BY c.nick
    """))

    section("stream_metrics row for stream 14 (roman_ius, 0 messages) -- sanity of zero-division")
    print(q("SELECT * FROM stream_sniper.stream_metrics WHERE stream_id = 14"))

main()
