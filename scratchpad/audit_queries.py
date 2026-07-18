from stream_sniper.database.core.connection_pool import database_entrypoint
from stream_sniper.database.core.decorators import with_cursor

@with_cursor
def q(cursor, sql):
    cursor.execute(sql)
    return cursor.fetchall()

@database_entrypoint
def main():
    print("=== creator / tracked counts ===")
    print(q("SELECT count(*) FROM stream_sniper.creator"))
    print(q("SELECT count(*) FROM stream_sniper.tracked_streamers"))

    print("=== stream count, date range ===")
    print(q("SELECT count(*), min(created_at), max(created_at) FROM stream_sniper.stream"))

    print("=== per-creator: stream count, last stream created_at, msg count ===")
    rows = q("""
        SELECT c.username, count(distinct s.id) as streams, max(s.created_at) as last_stream,
               count(m.id) as msgs
        FROM stream_sniper.creator c
        LEFT JOIN stream_sniper.stream s ON s.creator_id = c.id
        LEFT JOIN stream_sniper.message m ON m.stream_id = s.id
        GROUP BY c.username
        ORDER BY last_stream ASC NULLS FIRST
    """)
    for r in rows:
        print(r)

main()
