"""Mechanical SQL contract for fair atomic job claims."""

from contextlib import contextmanager
from unittest.mock import Mock

from stream_sniper.database.gateways.tracking import (
    processing_jobs_table_gateway as gateway,
)


def test_claim_recovers_expired_leases_and_uses_skip_locked(monkeypatch):
    cursor = Mock()
    cursor.fetchall.return_value = []

    @contextmanager
    def cursor_context():
        yield cursor

    monkeypatch.setattr(gateway, "write_cursor", cursor_context)

    assert (
        gateway.claim_processing_jobs_db(
            limit=2,
            max_retries=3,
            worker_token="worker",
            lease_seconds=60,
        )
        == []
    )

    sql, params = cursor.execute.call_args.args
    assert "lease_expires_at < CURRENT_TIMESTAMP" in sql
    assert "FOR UPDATE SKIP LOCKED" in sql
    assert "ORDER BY updated_at ASC, id ASC" in sql
    assert "worker_token = %(worker_token)s" in sql
    assert params["limit"] == 2
    assert params["max_retries"] == 3
    assert params["lease_seconds"] == 60


def test_enqueue_uses_the_database_identity_as_the_conflict_boundary(monkeypatch):
    cursor = Mock()
    cursor.fetchone.return_value = None

    @contextmanager
    def cursor_context():
        yield cursor

    monkeypatch.setattr(gateway, "write_cursor", cursor_context)

    assert gateway.enqueue_processing_job_db(3, 999) is None

    sql, params = cursor.execute.call_args.args
    assert "ON CONFLICT (tracked_streamer_id, twitch_vod_id) DO NOTHING" in sql
    assert "RETURNING id" in sql
    assert params == (3, 999, gateway.JOB_STATUS_PENDING)


def test_retry_is_an_atomic_failed_to_pending_transition(monkeypatch):
    cursor = Mock(rowcount=1)

    @contextmanager
    def cursor_context():
        yield cursor

    monkeypatch.setattr(gateway, "write_cursor", cursor_context)

    assert gateway.retry_failed_processing_job_db(7) is True

    sql, params = cursor.execute.call_args.args
    assert "WHERE id = %s AND status = %s" in sql
    assert "cancellation_requested_at = NULL" in sql
    assert params == (gateway.JOB_STATUS_PENDING, 7, gateway.JOB_STATUS_FAILED)


def test_completion_and_streamer_progress_are_one_leased_transition(monkeypatch):
    cursor = Mock(rowcount=1)

    @contextmanager
    def cursor_context():
        yield cursor

    monkeypatch.setattr(gateway, "write_cursor", cursor_context)

    assert gateway.complete_processing_job_and_advance_streamer_db(7, "lease-token") is True

    sql, params = cursor.execute.call_args.args
    assert "WITH completed AS" in sql
    assert "RETURNING tracked_streamer_id, twitch_vod_id" in sql
    assert "last_processed_vod_id = completed.twitch_vod_id" in sql
    assert "cancellation_requested_at IS NULL" in sql
    assert params == (gateway.JOB_STATUS_COMPLETED, 7, gateway.JOB_STATUS_IN_PROGRESS, "lease-token")


def test_cancellation_is_durable_and_worker_lease_scoped(monkeypatch):
    write = Mock(rowcount=1)
    read = Mock()
    read.fetchone.return_value = (1,)

    @contextmanager
    def write_context():
        yield write

    @contextmanager
    def read_context():
        yield read

    monkeypatch.setattr(gateway, "write_cursor", write_context)
    monkeypatch.setattr(gateway, "read_cursor", read_context)

    assert gateway.request_processing_job_cancellation_db(7) is True
    assert "cancellation_requested_at = CURRENT_TIMESTAMP" in write.execute.call_args.args[0]
    assert gateway.processing_job_cancellation_requested_db(7, "lease-token") is True
    assert read.execute.call_args.args[1] == (7, gateway.JOB_STATUS_IN_PROGRESS, "lease-token")
