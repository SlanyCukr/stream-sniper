"""Seed one deterministic analytics journey for the real Playwright stack."""

import os
from datetime import datetime, timedelta

import bcrypt
import psycopg2

CREATOR_ID = 990_001
STREAM_ID = 990_002
CHATTER_ID = 990_003
MESSAGE_TEXT_ID = 990_004
MESSAGE_ID = 990_005
ADMIN_USERNAME = "e2e_admin"
ADMIN_LOGIN_VALUE = os.environ["E2E_ADMIN_LOGIN_VALUE"]


def main() -> None:
    started_at = datetime(2026, 7, 15, 18, 0, 0)
    connection = psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        database=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
        port=int(os.environ["POSTGRES_PORT"]),
        options="-c search_path=stream_sniper",
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute("DELETE FROM tracked_streamers WHERE creator_id = %s", (CREATOR_ID,))
            cursor.execute("DELETE FROM message WHERE stream_id = %s OR id = %s", (STREAM_ID, MESSAGE_ID))
            cursor.execute("DELETE FROM stream_metrics WHERE stream_id = %s", (STREAM_ID,))
            cursor.execute("DELETE FROM stream_time_bucket WHERE stream_id = %s", (STREAM_ID,))
            cursor.execute("DELETE FROM stream WHERE id = %s OR twitch_id = %s", (STREAM_ID, 99_900_002))
            cursor.execute("DELETE FROM creator WHERE id = %s OR twitch_id = %s", (CREATOR_ID, 99_900_001))
            cursor.execute("DELETE FROM chatter WHERE id = %s", (CHATTER_ID,))
            cursor.execute("DELETE FROM message_text WHERE id = %s", (MESSAGE_TEXT_ID,))
            cursor.execute(
                "INSERT INTO creator (id, nick, display_name, profile_image_url, twitch_id) "
                "VALUES (%s, %s, %s, %s, %s)",
                (CREATOR_ID, "e2e_operator", "E2E Operator", "", 99_900_001),
            )
            password_hash = bcrypt.hashpw(ADMIN_LOGIN_VALUE.encode(), bcrypt.gensalt()).decode()
            cursor.execute(
                "INSERT INTO users (username, email, password_hash, role, is_active) "
                "VALUES (%s, %s, %s, 'admin', true) "
                "ON CONFLICT (username) DO UPDATE SET "
                "email = EXCLUDED.email, password_hash = EXCLUDED.password_hash, role = 'admin', is_active = true "
                "RETURNING id",
                (ADMIN_USERNAME, "e2e_admin@example.com", password_hash),
            )
            admin_id = cursor.fetchone()[0]
            cursor.execute(
                "INSERT INTO tracked_streamers "
                "(creator_id, twitch_username, display_name, is_active, processing_enabled, created_by) "
                "VALUES (%s, %s, %s, true, true, %s)",
                (CREATOR_ID, "e2e_operator", "E2E Operator", admin_id),
            )
            cursor.execute(
                'INSERT INTO stream (id, twitch_id, title, start, "end", message_count, creator_id) '
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    STREAM_ID,
                    99_900_002,
                    "Deterministic Analytics Stream",
                    started_at,
                    started_at + timedelta(minutes=10),
                    7,
                    CREATOR_ID,
                ),
            )
            cursor.execute("INSERT INTO chatter (id, nick) VALUES (%s, %s)", (CHATTER_ID, "e2e_viewer"))
            cursor.execute(
                "INSERT INTO message_text (id, text) VALUES (%s, %s)",
                (MESSAGE_TEXT_ID, "real boundary message"),
            )
            cursor.execute(
                "INSERT INTO message (id, chatter_id, stream_id, message_text_id, time, is_subscriber, emote_count) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (MESSAGE_ID, CHATTER_ID, STREAM_ID, MESSAGE_TEXT_ID, started_at, True, 0),
            )
            cursor.execute(
                "INSERT INTO stream_time_bucket (stream_id, bucket_minute, message_count, unique_chatters) "
                "VALUES (%s, %s, %s, %s)",
                (STREAM_ID, started_at, 7, 1),
            )
            cursor.execute(
                "INSERT INTO stream_metrics "
                "(stream_id, total_messages, unique_chatters, duration_seconds, messages_per_minute, "
                "peak_messages, peak_bucket_minute, new_chatters, returning_chatters) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                (STREAM_ID, 7, 1, 600, 0.7, 7, started_at, 1, 0),
            )
        connection.commit()
    finally:
        connection.close()


if __name__ == "__main__":
    main()
