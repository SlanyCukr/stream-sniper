"""Guards on the analytics rollup DDL (migration 0006 + create_table.sql snapshot).

Pins the removal of the redundant `stream_viewer_sample_session_idx`, which duplicated
the `stream_viewer_sample_uq` UNIQUE constraint (identical columns/order) and only added
write amplification on the tracking insert path.
"""

from pathlib import Path

_DB_DIR = Path(__file__).resolve().parents[3] / "stream_sniper" / "database"
_MIGRATION = _DB_DIR / "migrations" / "versions" / "0006_analytics_rollup_tables.py"
_MIGRATION_0008 = _DB_DIR / "migrations" / "versions" / "0008_analytics_expansion.py"
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


class TestAnalyticsExpansionDDL:
    """Guards on migration 0008 (analytics expansion tables)."""

    def test_revision_chain(self):
        text = _MIGRATION_0008.read_text()
        assert 'revision = "0008"' in text
        assert 'down_revision = "0007"' in text

    def test_creates_all_expansion_tables(self):
        text = _MIGRATION_0008.read_text()
        for table in (
            "stream_sniper.emote_dictionary",
            "stream_sniper.stream_emote_stats",
            "stream_sniper.stream_phrase_stats",
            "stream_sniper.stream_moment",
            "stream_sniper.moment_review",
            "stream_sniper.creator_audience",
            "stream_sniper.creator_overlap",
        ):
            assert f"CREATE TABLE IF NOT EXISTS {table}" in text

    def test_bucket_and_metrics_gain_nullable_metadata_columns(self):
        text = _MIGRATION_0008.read_text()
        # NULLABLE by design (unknown != 0 until re-rollup) — added, not created NOT NULL.
        assert "ADD COLUMN IF NOT EXISTS sub_messages   int NULL" in text
        assert "ADD COLUMN IF NOT EXISTS emote_messages int NULL" in text
        assert "ALTER TABLE stream_sniper.stream_time_bucket" in text
        assert "ALTER TABLE stream_sniper.stream_metrics" in text

    def test_share_columns_are_range_checked(self):
        text = _MIGRATION_0008.read_text()
        assert "sub_share IS NULL OR (sub_share >= 0 AND sub_share <= 1)" in text
        assert "emote_share IS NULL OR (emote_share >= 0 AND emote_share <= 1)" in text

    def test_overlap_enforces_ordered_pair(self):
        text = _MIGRATION_0008.read_text()
        assert "creator_overlap_order_ck CHECK (creator_a < creator_b)" in text

    def test_source_check_and_review_status_check(self):
        text = _MIGRATION_0008.read_text()
        assert "source IN ('bttv', 'twitch')" in text
        assert "status IN ('bookmarked', 'rejected')" in text

    def test_ddl_is_idempotent(self):
        text = _MIGRATION_0008.read_text()
        assert "CREATE INDEX IF NOT EXISTS" in text
        # No bare CREATE TABLE / CREATE INDEX that would fail a re-run.
        assert "CREATE TABLE stream_sniper." not in text
        assert "CREATE INDEX stream_sniper." not in text

    def test_downgrade_drops_tables_and_columns(self):
        text = _MIGRATION_0008.read_text()
        down = text.split("def downgrade")[1]
        for table in (
            "creator_overlap",
            "creator_audience",
            "moment_review",
            "stream_moment",
            "stream_phrase_stats",
            "stream_emote_stats",
            "emote_dictionary",
        ):
            assert f"DROP TABLE IF EXISTS stream_sniper.{table}" in down
        assert "DROP COLUMN IF EXISTS sub_messages" in down
        assert "DROP COLUMN IF EXISTS emote_messages" in down
