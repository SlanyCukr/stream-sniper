"""
Pytest configuration and fixtures for Stream Sniper tests.

This file contains shared test configuration, fixtures, and mock objects
used across the test suite for database, API, and collector components.
"""

import contextlib
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

# Production-style ASGI construction below uses the environment-loading boundary,
# so give that explicit configuration snapshot a test signing secret.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

# Disable startup cache warming for tests. The API lifespan otherwise warms the
# creators/stream-count caches from the real test DB, so endpoint tests (which mock
# the gateway functions) would read warmed data instead of exercising their mocks.
os.environ.setdefault("CACHE_WARM_ON_STARTUP", "false")

import psycopg2
import pytest
from fastapi.testclient import TestClient
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Configure test logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Test database configuration
TEST_DB_CONFIG = {
    "host": os.getenv("TEST_DB_HOST", "localhost"),
    "database": os.getenv("TEST_DB_NAME", "test_stream_sniper"),
    "user": os.getenv("TEST_DB_USER", "postgres"),
    "password": os.getenv("TEST_DB_PASSWORD", "password"),
    "port": os.getenv("TEST_DB_PORT", "5432"),
}

# The table-gateway functions under test open connections through the application's
# active database pool, whose executable boundaries read POSTGRES_*. Point it at the
# same test database the db_cursor fixture populates so gateway reads see the data.
os.environ["POSTGRES_HOST"] = TEST_DB_CONFIG["host"]
os.environ["POSTGRES_PORT"] = str(TEST_DB_CONFIG["port"])
os.environ["POSTGRES_USER"] = TEST_DB_CONFIG["user"]
os.environ["POSTGRES_PASSWORD"] = TEST_DB_CONFIG["password"]
os.environ["POSTGRES_DB"] = TEST_DB_CONFIG["database"]

MIGRATION_HEAD = "0017"


def _recreate_test_database() -> None:
    """Create a genuinely empty database for the migration-chain test path."""
    default_config = {**TEST_DB_CONFIG, "database": "postgres"}
    conn = psycopg2.connect(**default_config)
    try:
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s AND pid <> pg_backend_pid()",
                (TEST_DB_CONFIG["database"],),
            )
            database = sql.Identifier(TEST_DB_CONFIG["database"])
            cursor.execute(sql.SQL("DROP DATABASE IF EXISTS {}").format(database))
            cursor.execute(sql.SQL("CREATE DATABASE {}").format(database))
    finally:
        conn.close()


def _upgrade_test_database() -> None:
    """Run the same packaged Alembic entry point used by deployments."""
    from stream_sniper.database.commands.migrate import main as migrate

    migrate(["upgrade", "head"])


def _assert_migration_head(test_conn) -> None:
    """Prove the test schema includes representative baseline and later contracts."""
    with test_conn.cursor() as cursor:
        cursor.execute("SELECT version_num FROM stream_sniper.alembic_version")
        assert cursor.fetchone() == (MIGRATION_HEAD,)

        for relation in (
            "stream_sniper.tracking_heartbeat",
            "stream_sniper.stream_metrics",
            "stream_sniper.stream_context_sample",
        ):
            cursor.execute("SELECT to_regclass(%s)", (relation,))
            assert cursor.fetchone()[0] == relation

        cursor.execute(
            "SELECT indexname FROM pg_indexes WHERE schemaname = 'stream_sniper' "
            "AND indexname IN ('stream_twitch_session_uq', 'message_source_message_id_uq')"
        )
        assert {row[0] for row in cursor.fetchall()} == {
            "stream_twitch_session_uq",
            "message_source_message_id_uq",
        }


@pytest.fixture(autouse=True)
def _reset_global_state(request):
    """Isolate process-wide singletons between tests so ordering can't affect outcomes.

    The in-process cache would otherwise leak endpoint responses between
        tests (e.g. a success test populating a key that a later error test reads,
        so the mocked gateway is never called).
    """
    from stream_sniper.api.asgi import app
    from stream_sniper.database.core.connection_pool import enter_pool_scope, exit_pool_scope

    is_integration = "integration" in Path(str(request.fspath)).parts
    gateway_pool = request.getfixturevalue("integration_database_pool") if is_integration else MagicMock()
    # The shared production app owns and closes its runtime pool during TestClient
    # lifespans. Keep that disposable resource separate from the integration pool
    # bound for direct gateway calls across the test session.
    test_runtime_pool = MagicMock()
    app.state.runtime.database = test_runtime_pool
    app.state.database_pool = test_runtime_pool
    pool_token = enter_pool_scope(gateway_pool) if is_integration else None

    try:
        yield
    finally:
        if pool_token is not None:
            exit_pool_scope(pool_token)
        with contextlib.suppress(Exception):
            from stream_sniper.api.caching.cache import get_cache

            get_cache().flush_all()


@pytest.fixture(scope="session")
def test_db_connection():
    """
    Create a test database connection for the session.
    Build the schema from the packaged Alembic migration chain.
    """
    test_conn = None

    try:
        if os.getenv("TEST_DB_SCHEMA_READY", "false").lower() != "true":
            _recreate_test_database()
            _upgrade_test_database()

        test_conn = psycopg2.connect(**TEST_DB_CONFIG)
        test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        _assert_migration_head(test_conn)

        yield test_conn

    finally:
        if test_conn:
            test_conn.close()


@pytest.fixture(scope="session")
def integration_database_pool(test_db_connection):
    """Own the real pool explicitly used by integration gateway calls."""
    from stream_sniper.database.core.connection_pool import DatabaseConnectionPool, DatabasePoolConfig

    pool = DatabaseConnectionPool(
        DatabasePoolConfig(
            user=TEST_DB_CONFIG["user"],
            password=TEST_DB_CONFIG["password"],
            host=TEST_DB_CONFIG["host"],
            database=TEST_DB_CONFIG["database"],
            port=int(TEST_DB_CONFIG["port"]),
        )
    )
    pool.open()
    try:
        yield pool
    finally:
        pool.close_all_connections()


@pytest.fixture
def db_cursor(test_db_connection):
    """Provide a database cursor for individual tests."""
    cursor = test_db_connection.cursor()

    # Clear all tables before each test
    cursor.execute("SET search_path TO stream_sniper")
    cursor.execute("TRUNCATE users, message, message_text, chatter, stream, creator RESTART IDENTITY CASCADE")
    test_db_connection.commit()

    yield cursor

    cursor.close()


@pytest.fixture
def mock_connection_pool():
    """Mock database connection pool for unit tests."""
    mock_pool = MagicMock()
    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    # Configure mock behavior
    mock_pool.get_connection.return_value.__enter__.return_value = mock_connection
    mock_pool.get_cursor.return_value.__enter__.return_value = mock_cursor
    mock_pool.health_check.return_value = True
    mock_pool.get_pool_status.return_value = {"status": "active", "minconn": 2, "maxconn": 20}

    mock_connection.cursor.return_value = mock_cursor
    mock_cursor.fetchone.return_value = None
    mock_cursor.fetchall.return_value = []

    with patch("stream_sniper.database.core.decorators.get_active_pool", return_value=mock_pool):
        yield mock_pool, mock_connection, mock_cursor


@pytest.fixture
def api_client():
    """Create FastAPI test client."""
    from stream_sniper.api.asgi import app

    with patch("stream_sniper.database.core.decorators.get_active_pool"):
        client = TestClient(app)
        yield client


@pytest.fixture
def sample_creator_data():
    """Sample creator data for testing."""
    return {
        "nick": "test_streamer",
        "display_name": "Test Streamer",
        "profile_image_url": "https://example.com/profile.jpg",
        "twitch_id": 123456789,
    }


@pytest.fixture
def sample_stream_data():
    """Sample stream data for testing."""
    return {
        "twitch_id": 123,
        "title": "Epic Gaming Session",
        "start_time": datetime(2024, 1, 15, 20, 0, 0),
        "end_time": datetime(2024, 1, 15, 23, 30, 0),
        "thumbnail_url": "https://example.com/thumbnail.jpg",
        "message_count": 1250,
        "creator_id": 1,
    }


@pytest.fixture
def sample_chatter_data():
    """Sample chatter data for testing."""
    return [{"nick": "viewer123"}, {"nick": "chatty_user"}, {"nick": "stream_regular"}, {"nick": "new_viewer"}]


@pytest.fixture
def sample_message_data():
    """Sample message data for testing."""
    return [
        {"text": "Hello everyone!"},
        {"text": "Great stream!"},
        {"text": "@streamer keep it up!"},
        {"text": "Thanks for the content!"},
        {"text": "PogChamp"},
    ]


@pytest.fixture
def sample_chat_messages():
    """Sample chat messages for processor testing."""
    return [
        {"author": {"name": "viewer123"}, "message": "Hello everyone!", "time_in_seconds": 1642287015.0},
        {"author": {"name": "chatty_user"}, "message": "Great stream! @test_streamer", "time_in_seconds": 1642287045.0},
        {"author": {"name": "stream_regular"}, "message": "PogChamp", "time_in_seconds": 1642287075.0},
    ]


@pytest.fixture
def mock_twitch_api():
    """Mock TwitchAPI for testing."""
    from stream_sniper.collector.twitch_api import ArchivedVideo, CreatorProfile

    mock_api = Mock()
    mock_api.get_creator_profile.return_value = CreatorProfile(
        "123456789",
        "Test Streamer",
        "https://example.com/profile.jpg",
    )
    mock_api.get_archived_videos.return_value = [
        ArchivedVideo(
            id=123,
            stream_id=None,
            title="Epic Gaming Session",
            created_at=datetime(2024, 1, 15, 20),
            duration="3h30m",
            thumbnail_url="https://example.com/thumb.jpg",
        )
    ]
    return mock_api


@pytest.fixture
def temp_env_file():
    """Create temporary .env file for testing."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
        f.write("TEST_DB_HOST=localhost\n")
        f.write("TEST_DB_NAME=test_stream_sniper\n")
        f.write("TEST_DB_USER=postgres\n")
        f.write("TEST_DB_PASSWORD=password\n")
        f.write("TEST_DB_PORT=5432\n")
        temp_path = f.name

    yield temp_path

    os.unlink(temp_path)


@pytest.fixture
def mock_database_buffer():
    """Mock database buffer for testing."""
    mock_buffer = Mock()
    mock_buffer.add_item = Mock()
    mock_buffer.flush = Mock()
    return mock_buffer


# Test data helpers
def create_test_creator(cursor, creator_data=None):
    """Helper to create a test creator in the database."""
    if creator_data is None:
        creator_data = {
            "nick": "test_creator",
            "display_name": "Test Creator",
            "profile_image_url": "https://example.com/profile.jpg",
            "twitch_id": "123456",
        }

    cursor.execute(
        """
        INSERT INTO creator (nick, display_name, profile_image_url, twitch_id)
        VALUES (%(nick)s, %(display_name)s, %(profile_image_url)s, %(twitch_id)s)
        RETURNING id
    """,
        creator_data,
    )

    return cursor.fetchone()[0]


def create_test_stream(cursor, stream_data=None, creator_id=None):
    """Helper to create a test stream in the database."""
    if creator_id is None:
        creator_id = create_test_creator(cursor)

    if stream_data is None:
        stream_data = {
            "twitch_id": 123,
            "title": "Test Stream",
            "start": datetime(2024, 1, 15, 20, 0, 0),
            "end": datetime(2024, 1, 15, 23, 0, 0),
            "thumbnail_url": "https://example.com/thumb.jpg",
            "message_count": 100,
        }

    # Accept either the schema column names (start/end) or the legacy
    # start_time/end_time keys some fixtures still pass.
    start = stream_data.get("start", stream_data.get("start_time")) or datetime(2024, 1, 15, 20, 0, 0)
    end = stream_data.get("end", stream_data.get("end_time"))

    cursor.execute(
        """
        INSERT INTO stream (twitch_id, title, start, "end", thumbnail_url, message_count, creator_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """,
        (
            stream_data["twitch_id"],
            stream_data["title"],
            start,
            end,
            stream_data.get("thumbnail_url"),
            stream_data.get("message_count", 0),
            creator_id,
        ),
    )

    return cursor.fetchone()[0]


def create_test_chatter(cursor, nick="test_chatter"):
    """Helper to create a test chatter in the database."""
    cursor.execute("INSERT INTO chatter (nick) VALUES (%s) RETURNING id", (nick,))
    return cursor.fetchone()[0]


def create_test_message_text(cursor, text="Test message"):
    """Helper to create a test message text in the database."""
    cursor.execute("INSERT INTO message_text (text) VALUES (%s) RETURNING id", (text,))
    return cursor.fetchone()[0]
