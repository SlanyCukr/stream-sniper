"""Guards on the analytics rollup DDL (migration 0006 + create_table.sql snapshot).

Pins the removal of the redundant `stream_viewer_sample_session_idx`, which duplicated
the `stream_viewer_sample_uq` UNIQUE constraint (identical columns/order) and only added
write amplification on the tracking insert path.
"""

from pathlib import Path

_DB_DIR = Path(__file__).resolve().parents[3] / "stream_sniper" / "database"
_MIGRATION = _DB_DIR / "migrations" / "versions" / "0006_analytics_rollup_tables.py"
_CREATE_TABLE_SQL = _DB_DIR / "create_table.sql"


class TestViewerSampleIndexNotRedundant:
    def test_migration_has_no_redundant_session_index(self):
        text = _MIGRATION.read_text()
        # The UNIQUE constraint already provides the btree index on
        # (tracked_streamer_id, twitch_stream_session_id, sampled_at).
        assert "stream_viewer_sample_uq" in text
        assert "stream_viewer_sample_session_idx" not in text

    def test_create_table_snapshot_has_no_redundant_session_index(self):
        text = _CREATE_TABLE_SQL.read_text()
        assert "stream_viewer_sample_uq" in text
        assert "stream_viewer_sample_session_idx" not in text
