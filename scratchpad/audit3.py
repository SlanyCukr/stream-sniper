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
    section("tracked_streamers for the 22 zero-stream creators: last_stream_check, processing_enabled, last_processed_vod_id, created_at")
    print(q("""
        SELECT ts.twitch_username, ts.is_active, ts.processing_enabled, ts.last_stream_check,
               ts.last_processed_vod_id, ts.created_at
        FROM stream_sniper.tracked_streamers ts
        JOIN stream_sniper.creator c ON c.id = ts.creator_id
        WHERE NOT EXISTS (SELECT 1 FROM stream_sniper.stream s WHERE s.creator_id = c.id)
        ORDER BY ts.created_at
    """))

    section("processing_jobs status breakdown overall")
    print(q("SELECT status, count(*) FROM stream_sniper.processing_jobs GROUP BY status"))

    section("processing_jobs for those 22 zero-stream creators")
    print(q("""
        SELECT ts.twitch_username, pj.status, count(*)
        FROM stream_sniper.processing_jobs pj
        JOIN stream_sniper.tracked_streamers ts ON ts.id = pj.tracked_streamer_id
        JOIN stream_sniper.creator c ON c.id = ts.creator_id
        WHERE NOT EXISTS (SELECT 1 FROM stream_sniper.stream s WHERE s.creator_id = c.id)
        GROUP BY ts.twitch_username, pj.status
        ORDER BY 1
    """))

    section("processing_jobs failed with error_message sample (latest 10)")
    print(q("""
        SELECT ts.twitch_username, pj.status, pj.error_message, pj.created_at
        FROM stream_sniper.processing_jobs pj
        JOIN stream_sniper.tracked_streamers ts ON ts.id = pj.tracked_streamer_id
        WHERE pj.status = 'failed'
        ORDER BY pj.created_at DESC LIMIT 10
    """))

    section("stream_viewer_sample columns check + counts per tracked_streamer_id")
    print(q("SELECT count(*) FROM stream_sniper.stream_viewer_sample"))
    print(q("""
        SELECT ts.twitch_username, count(vs.id)
        FROM stream_sniper.tracked_streamers ts
        LEFT JOIN stream_sniper.stream_viewer_sample vs ON vs.tracked_streamer_id = ts.id
        GROUP BY ts.twitch_username
        ORDER BY 2 ASC
        LIMIT 10
    """))

    section("moment/overlap/copypasta/scene_event/context_sample row counts")
    for t in ["stream_moment","moment_review","creator_audience","creator_overlap",
              "stream_copypasta_stats","scene_event","stream_context_sample"]:
        print(t, q(f"SELECT count(*) FROM stream_sniper.{t}"))

    section("streams missing stream_chatter_stats -- which ones")
    print(q("""
        SELECT s.id, s.twitch_id, s.creator_id, s.start, s."end", s.message_count
        FROM stream_sniper.stream s
        WHERE NOT EXISTS (SELECT 1 FROM stream_sniper.stream_chatter_stats scs WHERE scs.stream_id = s.id)
    """))

    section("streams missing stream_metrics -- which ones")
    print(q("""
        SELECT s.id, s.twitch_id, s.creator_id, s.start, s."end", s.message_count
        FROM stream_sniper.stream s
        WHERE NOT EXISTS (SELECT 1 FROM stream_sniper.stream_metrics sm WHERE sm.stream_id = s.id)
    """))

    section("stream 123/125/126 -- message_count=0 but real msgs exist -- detail")
    print(q("""
        SELECT id, twitch_id, creator_id, start, "end", message_count FROM stream_sniper.stream
        WHERE id IN (103,123,125,126)
    """))

    section("scene_event date coverage")
    print(q("SELECT min(created_at), max(created_at), count(*) FROM stream_sniper.scene_event"))

    section("stream_moment date coverage + review status breakdown")
    print(q("SELECT count(*) FROM stream_sniper.moment_review"))
    print(q("SELECT status, count(*) FROM stream_sniper.moment_review GROUP BY status") )

main()
