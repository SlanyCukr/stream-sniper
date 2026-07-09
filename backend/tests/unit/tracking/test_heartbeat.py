"""Unit tests for the tracking liveness heartbeat (Postgres-backed)."""

from stream_sniper.tracking import heartbeat

SAMPLE = {
    "scheduler": {"running": True, "uptime_seconds": 12.0},
    "stream_monitor": {"running": True, "tracked_streamers_count": 2},
    "processing_queue": {"active_jobs": 1},
}


def test_write_delegates_to_gateway(monkeypatch):
    calls = {}

    def fake_upsert(component, status):
        calls["component"] = component
        calls["status"] = status
        return True

    monkeypatch.setattr(heartbeat, "upsert_heartbeat_db", fake_upsert)

    assert heartbeat.write_heartbeat(SAMPLE) is True
    assert calls["component"] == heartbeat.HEARTBEAT_COMPONENT
    assert calls["status"] == SAMPLE


def test_read_fresh_is_alive(monkeypatch):
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: (SAMPLE, 5.0))

    result = heartbeat.read_heartbeat()
    assert result is not None
    assert result["alive"] is True
    assert result["age_seconds"] == 5.0
    assert result["status"]["stream_monitor"]["running"] is True


def test_read_stale_is_not_alive(monkeypatch):
    stale_age = heartbeat.HEARTBEAT_STALE_AFTER + 10
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: (SAMPLE, stale_age))

    result = heartbeat.read_heartbeat()
    assert result is not None
    assert result["alive"] is False


def test_read_at_threshold_is_alive(monkeypatch):
    # age exactly at the threshold is still considered alive (<=).
    monkeypatch.setattr(
        heartbeat, "select_heartbeat_db", lambda c: (SAMPLE, float(heartbeat.HEARTBEAT_STALE_AFTER))
    )
    result = heartbeat.read_heartbeat()
    assert result is not None and result["alive"] is True


def test_read_missing_row_returns_none(monkeypatch):
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: None)
    assert heartbeat.read_heartbeat() is None


def test_read_handles_null_status(monkeypatch):
    monkeypatch.setattr(heartbeat, "select_heartbeat_db", lambda c: (None, 1.0))
    result = heartbeat.read_heartbeat()
    assert result is not None
    assert result["status"] == {}
    assert result["alive"] is True


def test_delete_delegates_to_gateway(monkeypatch):
    seen = {}

    def fake_delete(component):
        seen["component"] = component
        return True

    monkeypatch.setattr(heartbeat, "delete_heartbeat_db", fake_delete)
    assert heartbeat.delete_heartbeat() is True
    assert seen["component"] == heartbeat.HEARTBEAT_COMPONENT
