"""Unit tests for the highlight-queue endpoints (/moments, review mutations).

The moment router is mounted on the shared app by the integration wiring step, so these tests
mount it on a minimal FastAPI app with the real rate limiter, patch gateways by their import
path in ``moment_endpoints``, and use an always-miss cache. Admin gating is exercised by
overriding ``get_current_user`` (the dependency ``get_current_admin_user`` builds on).
"""

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from stream_sniper.api.auth import get_current_user
from stream_sniper.api.moment_endpoints import router
from stream_sniper.api.rate_limiter import setup_rate_limiting
from stream_sniper.database.stream_moment_table_gateway import (
    select_moment_exists_db,
    select_moment_queue_db,
)
from tests.conftest import create_test_creator, create_test_stream


def _client() -> TestClient:
    app = FastAPI()
    setup_rate_limiting(app)
    app.include_router(router)
    return TestClient(app)


def _admin_client() -> TestClient:
    client = _client()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, username="admin", role="admin", is_active=True
    )
    return client


def _user_client() -> TestClient:
    client = _client()
    client.app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=2, username="joe", role="user", is_active=True
    )
    return client


def _miss_cache():
    cache = Mock()
    cache._generate_key = Mock(return_value="test-cache-key")
    cache.get = Mock(return_value=None)
    cache.set = Mock(return_value=True)
    return cache


def _queue_row(status=None):
    return (
        42,                       # stream_id
        "Big Stream",             # title
        "2024-01-15T20:00:00",    # start
        "vod999",                 # twitch_id
        7,                        # creator_id
        "TheCreator",             # creator_display_name
        "2024-01-15T20:10:00",    # bucket_minute
        600,                      # offset_seconds
        120,                      # message_count
        5.0,                      # baseline
        24.0,                     # ratio
        40,                       # unique_chatters
        0.25,                     # sub_share
        0.5,                      # emote_share
        [{"phrase": "pog", "count": 9, "lift": 3.2}],  # top_phrases
        [{"text": "POG", "count": 5}],                 # sample_messages
        status,                   # review status (None -> pending)
    )


class TestMomentQueueEndpoint:
    @patch("stream_sniper.api.moment_endpoints.get_cache")
    @patch("stream_sniper.api.moment_endpoints.select_moment_queue_db")
    def test_success_maps_items_total_and_pending_status(self, mock_queue, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_queue.return_value = ([_queue_row(None)], 3)

        response = _client().get("/moments?status=pending&creator_id=7&limit=50&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["limit"] == 50
        assert data["offset"] == 0
        item = data["items"][0]
        assert item["stream_id"] == 42
        assert item["creator_display_name"] == "TheCreator"
        assert item["ratio"] == 24.0
        assert item["status"] == "pending"  # NULL review row -> pending
        assert item["top_phrases"] == [{"phrase": "pog", "count": 9, "lift": 3.2}]
        mock_queue.assert_called_once_with("pending", 7, 50, 0)

    @patch("stream_sniper.api.moment_endpoints.get_cache")
    @patch("stream_sniper.api.moment_endpoints.select_moment_queue_db")
    def test_reviewed_status_passthrough(self, mock_queue, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_queue.return_value = ([_queue_row("bookmarked")], 1)

        response = _client().get("/moments?status=bookmarked")

        assert response.status_code == 200
        assert response.json()["items"][0]["status"] == "bookmarked"
        mock_queue.assert_called_once_with("bookmarked", None, 50, 0)

    @patch("stream_sniper.api.moment_endpoints.get_cache")
    @patch("stream_sniper.api.moment_endpoints.select_moment_queue_db")
    def test_default_status_is_empty_all(self, mock_queue, mock_get_cache):
        mock_get_cache.return_value = _miss_cache()
        mock_queue.return_value = ([], 0)

        response = _client().get("/moments")

        assert response.status_code == 200
        mock_queue.assert_called_once_with("", None, 50, 0)

    def test_invalid_status_rejected(self):
        response = _client().get("/moments?status=bogus")
        assert response.status_code == 422


class TestSetMomentReview:
    @patch("stream_sniper.api.moment_endpoints.invalidate_cache_pattern")
    @patch("stream_sniper.api.moment_endpoints.upsert_moment_review_db")
    @patch("stream_sniper.api.moment_endpoints.select_moment_exists_db")
    def test_admin_upsert_returns_status_and_invalidates(
        self, mock_exists, mock_upsert, mock_invalidate
    ):
        mock_exists.return_value = True
        mock_upsert.return_value = "2024-01-15T21:00:00"

        response = _admin_client().put(
            "/stream/42/moments/2024-01-15T20:10:00/review",
            json={"status": "bookmarked"},
        )

        assert response.status_code == 200
        assert response.json() == {
            "status": "bookmarked",
            "updated_at": "2024-01-15T21:00:00",
        }
        mock_upsert.assert_called_once_with(42, "2024-01-15T20:10:00", "bookmarked")
        mock_invalidate.assert_any_call("stream_timeline:*")
        mock_invalidate.assert_any_call("moments_queue:*")

    @patch("stream_sniper.api.moment_endpoints.invalidate_cache_pattern")
    @patch("stream_sniper.api.moment_endpoints.upsert_moment_review_db")
    @patch("stream_sniper.api.moment_endpoints.select_moment_exists_db")
    def test_missing_moment_404_no_write_no_invalidate(
        self, mock_exists, mock_upsert, mock_invalidate
    ):
        mock_exists.return_value = False

        response = _admin_client().put(
            "/stream/42/moments/2024-01-15T20:10:00/review",
            json={"status": "bookmarked"},
        )

        assert response.status_code == 404
        mock_upsert.assert_not_called()
        mock_invalidate.assert_not_called()

    def test_invalid_status_rejected(self):
        response = _admin_client().put(
            "/stream/42/moments/2024-01-15T20:10:00/review",
            json={"status": "loved"},
        )
        assert response.status_code == 422

    def test_unauthenticated_rejected(self):
        response = _client().put(
            "/stream/42/moments/2024-01-15T20:10:00/review",
            json={"status": "bookmarked"},
        )
        assert response.status_code in (401, 403)

    def test_non_admin_forbidden(self):
        response = _user_client().put(
            "/stream/42/moments/2024-01-15T20:10:00/review",
            json={"status": "bookmarked"},
        )
        assert response.status_code == 403


class TestClearMomentReview:
    @patch("stream_sniper.api.moment_endpoints.invalidate_cache_pattern")
    @patch("stream_sniper.api.moment_endpoints.delete_moment_review_db")
    @patch("stream_sniper.api.moment_endpoints.select_moment_exists_db")
    def test_admin_clear_returns_nulls_and_invalidates(
        self, mock_exists, mock_delete, mock_invalidate
    ):
        mock_exists.return_value = True
        mock_delete.return_value = 1

        response = _admin_client().delete("/stream/42/moments/2024-01-15T20:10:00/review")

        assert response.status_code == 200
        assert response.json() == {"status": None, "updated_at": None}
        mock_delete.assert_called_once_with(42, "2024-01-15T20:10:00")
        mock_invalidate.assert_any_call("stream_timeline:*")
        mock_invalidate.assert_any_call("moments_queue:*")

    @patch("stream_sniper.api.moment_endpoints.invalidate_cache_pattern")
    @patch("stream_sniper.api.moment_endpoints.delete_moment_review_db")
    @patch("stream_sniper.api.moment_endpoints.select_moment_exists_db")
    def test_missing_moment_404(self, mock_exists, mock_delete, mock_invalidate):
        mock_exists.return_value = False

        response = _admin_client().delete("/stream/42/moments/2024-01-15T20:10:00/review")

        assert response.status_code == 404
        mock_delete.assert_not_called()
        mock_invalidate.assert_not_called()

    def test_unauthenticated_rejected(self):
        response = _client().delete("/stream/42/moments/2024-01-15T20:10:00/review")
        assert response.status_code in (401, 403)

    def test_non_admin_forbidden(self):
        response = _user_client().delete("/stream/42/moments/2024-01-15T20:10:00/review")
        assert response.status_code == 403


# --- DB-backed coverage for the queue gateway SQL (endpoint tests above mock it) ---

_QUEUE_DDL = """
SET search_path TO stream_sniper;
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
"""


@pytest.fixture
def queue_db(db_cursor):
    db_cursor.execute(_QUEUE_DDL)
    db_cursor.execute("TRUNCATE moment_review, stream_moment RESTART IDENTITY CASCADE")
    db_cursor.connection.commit()
    return db_cursor


def _insert_moment(cursor, stream_id, minute, ratio):
    bucket = datetime(2024, 1, 15, 20, minute, 0)
    cursor.execute(
        """
        INSERT INTO stream_moment
            (stream_id, bucket_minute, offset_seconds, message_count, baseline, ratio,
             unique_chatters, sub_share, emote_share, top_phrases, sample_messages)
        VALUES (%s, %s, %s, %s, %s, %s, %s, NULL, NULL, NULL, NULL)
        """,
        (stream_id, bucket, minute * 60, 100, 5.0, ratio, 40),
    )
    return bucket


class TestMomentQueueGateway:
    def test_pending_filter_creator_filter_total_and_status(self, queue_db):
        c1 = create_test_creator(queue_db, {"nick": "c1", "display_name": "C1",
                                            "profile_image_url": "x", "twitch_id": "1"})
        c2 = create_test_creator(queue_db, {"nick": "c2", "display_name": "C2",
                                            "profile_image_url": "x", "twitch_id": "2"})
        s1 = create_test_stream(queue_db, {"twitch_id": "s1", "title": "S1"}, c1)
        s2 = create_test_stream(queue_db, {"twitch_id": "s2", "title": "S2"}, c2)
        b_low = _insert_moment(queue_db, s1, 5, 4.0)
        b_high = _insert_moment(queue_db, s1, 10, 20.0)
        _insert_moment(queue_db, s2, 15, 9.0)
        # Bookmark the high-ratio moment on s1.
        queue_db.execute(
            "INSERT INTO moment_review (stream_id, bucket_minute, status) VALUES (%s, %s, 'bookmarked')",
            (s1, b_high),
        )
        queue_db.connection.commit()

        # Pending across all creators excludes the bookmarked one -> 2 rows.
        rows, total = select_moment_queue_db("pending", None, 50, 0)
        assert total == 2
        assert all(r[16] is None for r in rows)

        # Pending restricted to creator 1 -> only the low-ratio moment on s1.
        rows, total = select_moment_queue_db("pending", c1, 50, 0)
        assert total == 1
        assert rows[0][0] == s1
        assert rows[0][6] == b_low.strftime("%Y-%m-%dT%H:%M:%S")
        assert rows[0][5] == "C1"  # creator display_name

        # Bookmarked filter -> the reviewed moment, status surfaced.
        rows, total = select_moment_queue_db("bookmarked", None, 50, 0)
        assert total == 1
        assert rows[0][16] == "bookmarked"
        assert rows[0][6] == b_high.strftime("%Y-%m-%dT%H:%M:%S")

        # No status filter -> all three moments; reviewed first, then pending by ratio DESC.
        rows, total = select_moment_queue_db("", None, 50, 0)
        assert total == 3
        assert rows[0][16] == "bookmarked"          # reviewed first (updated_at DESC NULLS LAST)
        assert rows[1][10] >= rows[2][10]           # remaining pending ordered by ratio DESC

    def test_pagination_limit_offset(self, queue_db):
        c1 = create_test_creator(queue_db, {"nick": "cc", "display_name": "CC",
                                            "profile_image_url": "x", "twitch_id": "9"})
        s1 = create_test_stream(queue_db, {"twitch_id": "sp", "title": "SP"}, c1)
        for i, ratio in enumerate([30.0, 20.0, 10.0]):
            _insert_moment(queue_db, s1, 5 + i, ratio)
        queue_db.connection.commit()

        page1, total = select_moment_queue_db("pending", None, 2, 0)
        page2, _ = select_moment_queue_db("pending", None, 2, 2)
        assert total == 3
        assert len(page1) == 2 and len(page2) == 1
        assert page1[0][10] == 30.0  # highest ratio first

    def test_moment_exists(self, queue_db):
        c1 = create_test_creator(queue_db, {"nick": "ce", "display_name": "CE",
                                            "profile_image_url": "x", "twitch_id": "7"})
        s1 = create_test_stream(queue_db, {"twitch_id": "se", "title": "SE"}, c1)
        bucket = _insert_moment(queue_db, s1, 12, 8.0)
        queue_db.connection.commit()

        assert select_moment_exists_db(s1, bucket.strftime("%Y-%m-%dT%H:%M:%S")) is True
        assert select_moment_exists_db(s1, "2024-01-15T23:59:00") is False
