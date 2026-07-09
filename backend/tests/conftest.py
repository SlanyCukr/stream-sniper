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
from unittest.mock import MagicMock, Mock, patch

# Ensure a JWT signing secret exists before any application module is imported.
# stream_sniper.api.auth fails fast at import time if neither JWT_SECRET_KEY nor
# SECRET_KEY is set, which would otherwise break collection of API test modules.
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")

# Disable startup cache warming for tests. The API lifespan otherwise warms the
# creators/stream-count caches from the real test DB, so endpoint tests (which mock
# the gateway functions) would read warmed data instead of exercising their mocks.
os.environ.setdefault("CACHE_WARM_ON_STARTUP", "false")

import psycopg2
import pytest
from fastapi.testclient import TestClient
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
# global connection pool (stream_sniper.database.connection_pool.get_pool), which
# reads the POSTGRES_* env names (with legacy fallbacks). Point that pool at the
# same test database the db_cursor fixture populates so gateway reads see the data.
os.environ["POSTGRES_HOST"] = TEST_DB_CONFIG["host"]
os.environ["POSTGRES_PORT"] = str(TEST_DB_CONFIG["port"])
os.environ["POSTGRES_USER"] = TEST_DB_CONFIG["user"]
os.environ["POSTGRES_PASSWORD"] = TEST_DB_CONFIG["password"]
os.environ["POSTGRES_DB"] = TEST_DB_CONFIG["database"]

# Schema creation SQL
# Kept in sync with stream_sniper/database/create_table.sql and the column names
# used by the table gateways (e.g. stream.start / stream."end", message.time).
# Note: twitch_id columns are VARCHAR here so string-based test ids work, and
# stream.start is left nullable so fixtures that omit it still insert.
SCHEMA_SQL = """
CREATE SCHEMA IF NOT EXISTS stream_sniper;
SET search_path TO stream_sniper;

-- Chatter table
CREATE TABLE IF NOT EXISTS chatter (
    id   SERIAL PRIMARY KEY,
    nick VARCHAR(255) NOT NULL,
    CONSTRAINT chatter_name_uindex UNIQUE (nick)
);

-- Creator table
CREATE TABLE IF NOT EXISTS creator (
    id                SERIAL PRIMARY KEY,
    nick              VARCHAR(255) NOT NULL,
    display_name      VARCHAR(255) NOT NULL,
    profile_image_url VARCHAR(255) NOT NULL,
    twitch_id         VARCHAR(255),
    CONSTRAINT creator_nick_uindex UNIQUE (nick)
);

-- Stream table
CREATE TABLE IF NOT EXISTS stream (
    id            SERIAL PRIMARY KEY,
    twitch_id     VARCHAR(255) NOT NULL,
    title         VARCHAR(255) NOT NULL,
    start         TIMESTAMP,
    "end"         TIMESTAMP,
    thumbnail_url VARCHAR(255),
    message_count INTEGER NOT NULL DEFAULT 0,
    creator_id    INTEGER REFERENCES creator (id),
    CONSTRAINT stream__twitch_id_uindex UNIQUE (twitch_id)
);

-- Message text table (for deduplication)
CREATE TABLE IF NOT EXISTS message_text (
    id   SERIAL PRIMARY KEY,
    text VARCHAR(255) NOT NULL,
    CONSTRAINT text_uq UNIQUE (text)
);

-- Message table
CREATE TABLE IF NOT EXISTS message (
    id                SERIAL PRIMARY KEY,
    chatter_id        INTEGER REFERENCES chatter (id),
    tagged_chatter_id INTEGER REFERENCES chatter (id),
    stream_id         INTEGER REFERENCES stream (id),
    message_text_id   BIGINT NOT NULL REFERENCES message_text (id),
    time              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


@pytest.fixture(autouse=True)
def _reset_global_state():
    """Isolate process-wide singletons between tests so ordering can't affect outcomes.

    Two shared singletons otherwise leak state across tests:
      * The DB connection pool -- the API lifespan shutdown calls ``close_pool()``,
        which nulls the module-level instance but leaves the class-level
        ``DatabaseConnectionPool`` singleton half-closed (``_pool is None``). A later
        test calling ``get_pool()`` would then hit "Connection pool not initialized".
      * The in-process cache -- cached endpoint responses would otherwise leak between
        tests (e.g. a success test populating a key that a later error test reads,
        so the mocked gateway is never called).

    Resetting both after every test forces a clean re-initialization on next use.
    """
    yield

    from stream_sniper.database import connection_pool as _cp

    with contextlib.suppress(Exception):
        if _cp._pool_instance is not None:
            _cp._pool_instance.close_all_connections()
    _cp._pool_instance = None
    _cp.DatabaseConnectionPool._instance = None

    with contextlib.suppress(Exception):
        from stream_sniper.api.cache import get_cache

        get_cache().flush_all()


@pytest.fixture(scope="session")
def test_db_connection():
    """
    Create a test database connection for the session.
    Creates test database and schema if they don't exist.
    """
    # First connect to default database to create test database
    default_config = TEST_DB_CONFIG.copy()
    default_config["database"] = "postgres"

    conn = None
    test_conn = None

    try:
        # Connect to default database
        conn = psycopg2.connect(**default_config)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create test database if it doesn't exist
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{TEST_DB_CONFIG['database']}'")
        if not cursor.fetchone():
            cursor.execute(f"CREATE DATABASE {TEST_DB_CONFIG['database']}")
            logger.info(f"Created test database: {TEST_DB_CONFIG['database']}")

        cursor.close()
        conn.close()

        # Connect to test database
        test_conn = psycopg2.connect(**TEST_DB_CONFIG)
        test_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)

        # Create schema and tables
        cursor = test_conn.cursor()
        cursor.execute(SCHEMA_SQL)
        cursor.close()

        yield test_conn

    finally:
        if test_conn:
            test_conn.close()


@pytest.fixture
def db_cursor(test_db_connection):
    """Provide a database cursor for individual tests."""
    cursor = test_db_connection.cursor()

    # Clear all tables before each test
    cursor.execute("SET search_path TO stream_sniper")
    cursor.execute("TRUNCATE message, message_text, chatter, stream, creator RESTART IDENTITY CASCADE")
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

    with patch("stream_sniper.database.decorators.get_pool", return_value=mock_pool):
        yield mock_pool, mock_connection, mock_cursor


@pytest.fixture
def api_client():
    """Create FastAPI test client."""
    from stream_sniper.api.api import app

    with patch("stream_sniper.database.decorators.get_pool"):
        client = TestClient(app)
        yield client


@pytest.fixture
def sample_creator_data():
    """Sample creator data for testing."""
    return {
        "nick": "test_streamer",
        "display_name": "Test Streamer",
        "profile_image_url": "https://example.com/profile.jpg",
        "twitch_id": "123456789",
    }


@pytest.fixture
def sample_stream_data():
    """Sample stream data for testing."""
    return {
        "twitch_id": "stream_123",
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
    mock_api = Mock()
    mock_api.get_creator_info.return_value = ("Test Streamer", "https://example.com/profile.jpg")
    mock_api.get_creator_twitch_id.return_value = "123456789"
    mock_api.get_videos.return_value = [
        {
            "id": "video_123",
            "title": "Epic Gaming Session",
            "created_at": "2024-01-15T20:00:00Z",
            "duration": "3h30m",
            "thumbnail_url": "https://example.com/thumb.jpg",
        }
    ]
    return mock_api


@pytest.fixture
def mock_chat_downloader():
    """Mock IRC chat downloader for testing."""
    mock_downloader = Mock()
    mock_downloader.download_chat.return_value = (
        [{"author": {"name": "viewer123"}, "message": "Hello!", "time_in_seconds": 1642287015.0}],  # chat messages
        "stream_123",  # twitch_stream_id
        "2024-01-15T20:00:00Z",  # started_at
        "Test Stream",  # title
        "3h30m",  # duration
        "https://example.com/thumb.jpg",  # thumbnail_url
    )
    return mock_downloader


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
    mock_buffer.call_db_function = Mock()
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
            "twitch_id": "stream_123",
            "title": "Test Stream",
            "start": datetime(2024, 1, 15, 20, 0, 0),
            "end": datetime(2024, 1, 15, 23, 0, 0),
            "thumbnail_url": "https://example.com/thumb.jpg",
            "message_count": 100,
        }

    # Accept either the schema column names (start/end) or the legacy
    # start_time/end_time keys some fixtures still pass.
    start = stream_data.get("start", stream_data.get("start_time"))
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
