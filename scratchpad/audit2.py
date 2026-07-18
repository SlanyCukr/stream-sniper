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
    section("creator / tracked_streamers counts")
    print(q("SELECT count(*) FROM stream_sniper.creator"))
    print(q("SELECT count(*), count(*) FILTER (WHERE is_active) FROM stream_sniper.tracked_streamers"))

    section("stream count, date range (start/end)")
    print(q("SELECT count(*), min(start), max(start) FROM stream_sniper.stream"))
    print(q("SELECT count(*) FROM stream_sniper.stream WHERE \"end\" IS NULL"))

    section("per-creator: stream count, last stream start, msg count, days since last stream")
    rows = q("""
        SELECT c.nick, count(distinct s.id) as streams, max(s.start) as last_stream,
               count(m.id) as msgs,
               extract(day from now() - max(s.start)) as days_since
        FROM stream_sniper.creator c
        LEFT JOIN stream_sniper.tracked_streamers ts ON ts.creator_id = c.id
        LEFT JOIN stream_sniper.stream s ON s.creator_id = c.id
        LEFT JOIN stream_sniper.message m ON m.stream_id = s.id
        GROUP BY c.nick
        ORDER BY last_stream ASC NULLS FIRST
    """)
    for r in rows:
        print(r)

    section("tracked creators with ZERO streams ever")
    print(q("""
        SELECT c.nick FROM stream_sniper.creator c
        JOIN stream_sniper.tracked_streamers ts ON ts.creator_id = c.id AND ts.is_active
        LEFT JOIN stream_sniper.stream s ON s.creator_id = c.id
        WHERE s.id IS NULL
    """))

    section("tracked (active) creators with no stream in last 30 days")
    print(q("""
        SELECT c.nick, max(s.start) as last_stream
        FROM stream_sniper.creator c
        JOIN stream_sniper.tracked_streamers ts ON ts.creator_id = c.id AND ts.is_active
        LEFT JOIN stream_sniper.stream s ON s.creator_id = c.id
        GROUP BY c.nick
        HAVING max(s.start) < now() - interval '30 days' OR max(s.start) IS NULL
        ORDER BY last_stream ASC NULLS FIRST
    """))

    section("streams marked 'complete' (end not null) but 0 messages")
    print(q("""
        SELECT count(*) FROM stream_sniper.stream s
        WHERE s."end" IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM stream_sniper.message m WHERE m.stream_id = s.id)
    """))

    section("streams with message_count field mismatching actual message rows")
    print(q("""
        SELECT s.id, s.message_count, actual.cnt FROM stream_sniper.stream s
        JOIN (SELECT stream_id, count(*) cnt FROM stream_sniper.message GROUP BY stream_id) actual
          ON actual.stream_id = s.id
        WHERE s.message_count != actual.cnt
        LIMIT 20
    """))

    section("orphan messages: stream_id not null but no matching stream")
    print(q("""
        SELECT count(*) FROM stream_sniper.message m
        WHERE m.stream_id IS NOT NULL
        AND NOT EXISTS (SELECT 1 FROM stream_sniper.stream s WHERE s.id = m.stream_id)
    """))

    section("messages with NULL stream_id")
    print(q("SELECT count(*) FROM stream_sniper.message WHERE stream_id IS NULL"))

    section("messages with NULL chatter_id")
    print(q("SELECT count(*) FROM stream_sniper.message WHERE chatter_id IS NULL"))

    section("duplicate twitch_id in stream (should be unique - constraint exists, but check dupes anyway)")
    print(q("""
        SELECT twitch_id, count(*) FROM stream_sniper.stream
        GROUP BY twitch_id HAVING count(*) > 1
    """))

    section("duplicate twitch_id in creator")
    print(q("""
        SELECT twitch_id, count(*) FROM stream_sniper.creator
        WHERE twitch_id IS NOT NULL
        GROUP BY twitch_id HAVING count(*) > 1
    """))

    section("chatter.is_bot: total chatters, marked bots, breakdown by bot_reason")
    print(q("SELECT count(*) FROM stream_sniper.chatter"))
    print(q("SELECT count(*) FROM stream_sniper.chatter WHERE is_bot IS TRUE"))
    print(q("SELECT bot_reason, count(*) FROM stream_sniper.chatter WHERE is_bot IS TRUE GROUP BY bot_reason ORDER BY 2 DESC"))

    section("known-bot nicks (from repo KNOWN_BOTS) present in chatter but NOT marked is_bot")
    known_bots = ["nightbot","streamelements","streamlabs","moobot","fossabot","wizebot","botisimo","coebot",
      "deepbot","phantombot","sery_bot","soundalerts","commanderroot","anotherttvviewer","own3d","tangiabot",
      "kofistreambot","blerp","pokemoncommunitygame","sound_alerts","regressz","lurxx","streamholics",
      "aliceydra","creatisbot","tarsai","frostytoolsdotcom","dinu","peepostreambot","supibot","restreambot",
      "botrixoficial","herbot_","spajkk_irl_bot"]
    in_list = "'" + "','".join(known_bots) + "'"
    print(q(f"""
        SELECT nick, is_bot, bot_reason FROM stream_sniper.chatter
        WHERE lower(nick) IN ({in_list}) AND (is_bot IS NOT TRUE)
    """))

    section("rollup coverage: streams missing stream_metrics rows")
    print(q("""
        SELECT count(*) FROM stream_sniper.stream s
        WHERE NOT EXISTS (SELECT 1 FROM stream_sniper.stream_metrics sm WHERE sm.stream_id = s.id)
    """))
    section("stream_metrics total rows vs stream total rows")
    print(q("SELECT count(*) FROM stream_sniper.stream_metrics"))
    print(q("SELECT count(*) FROM stream_sniper.stream"))

    section("streams missing stream_chatter_stats entirely")
    print(q("""
        SELECT count(*) FROM stream_sniper.stream s
        WHERE NOT EXISTS (SELECT 1 FROM stream_sniper.stream_chatter_stats scs WHERE scs.stream_id = s.id)
    """))

    section("streams missing stream_viewer_sample (viewer samples)")
    print(q("""
        SELECT count(*) FROM stream_sniper.stream s
        WHERE NOT EXISTS (SELECT 1 FROM stream_sniper.stream_viewer_sample vs WHERE vs.stream_id = s.id)
    """))
    print(q("SELECT count(*) FROM stream_sniper.stream_viewer_sample"))

    section("NULL rate in stream.end (never-ended streams) by age")
    print(q("""
        SELECT count(*) FILTER (WHERE "end" IS NULL AND start < now() - interval '1 day') as stale_open,
               count(*) FILTER (WHERE "end" IS NULL) as total_open
        FROM stream_sniper.stream
    """))

    section("stream_moment coverage + creator_overlap + creator_audience row counts")
    print(q("SELECT count(*) FROM stream_sniper.stream_moment"))
    print(q("SELECT count(*) FROM stream_sniper.moment_review"))
    print(q("SELECT count(*) FROM stream_sniper.creator_audience"))
    print(q("SELECT count(*) FROM stream_sniper.creator_overlap"))
    print(q("SELECT count(*) FROM stream_sniper.stream_copypasta_stats"))
    print(q("SELECT count(*) FROM stream_sniper.scene_event"))
    print(q("SELECT count(*) FROM stream_sniper.stream_context_sample"))

    section("scene_event: date range and per-stream coverage vs total streams")
    print(q("SELECT min(created_at), max(created_at) FROM stream_sniper.scene_event") or q("SELECT count(*) FROM stream_sniper.scene_event"))

main()
