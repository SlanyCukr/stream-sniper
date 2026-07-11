"""Derived-analytics rollup engine and backfill CLI.

The rollup engine recomputes per-stream and per-creator aggregate tables
(stream_time_bucket, stream_chatter_stats, stream_metrics, creator_chatter_stats)
from the raw `message` rows. Rollups are idempotent DELETE+INSERT/UPSERT recomputes.
"""
