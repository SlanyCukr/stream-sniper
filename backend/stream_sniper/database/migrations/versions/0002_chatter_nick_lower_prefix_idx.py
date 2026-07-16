"""chatter lower(nick) prefix index, built CONCURRENTLY

Adds stream_sniper.chatter_nick_lower_prefix_idx = lower(nick) text_pattern_ops,
enabling `lower(nick) LIKE 'foo%'` to use an index under a non-C collation
(GET /chatters/search autocomplete).

CREATE/DROP INDEX CONCURRENTLY cannot run inside a transaction; Alembic wraps
migrations in one by default, so both directions use autocommit_block(). Offline
(--sql) mode cannot honor autocommit_block (it emits BEGIN/COMMIT around each
migration), so this revision REFUSES to run offline.

Operational caveats:
  * IF NOT EXISTS / IF EXISTS make re-runs safe.
  * INVALID-index trap: if a CONCURRENTLY build is interrupted, Postgres leaves an
    INVALID index and IF NOT EXISTS then SKIPS the rebuild. If upgrade fails mid
    index, manually `DROP INDEX CONCURRENTLY stream_sniper.chatter_nick_lower_prefix_idx;`
    before re-running. The prod runbook and verification recipe assert indisvalid = 't'.
  * Do not add other DDL to this file — autocommit_block() would commit it prematurely.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def _guard_online() -> None:
    # MigrationContext exposes offline mode via `.as_sql` (True under --sql);
    # is_offline_mode() lives on EnvironmentContext, not here.
    if op.get_context().as_sql:
        raise RuntimeError(
            "0002 builds an index CONCURRENTLY and cannot be emitted for offline "
            "(--sql) execution; run it online (stream-sniper-migrate / uv run alembic upgrade)."
        )


def upgrade() -> None:
    _guard_online()
    # autocommit_block() unconditionally commits the preceding tx, so this DDL
    # MUST be alone in its own migration (it is).
    with op.get_context().autocommit_block():
        op.execute(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS chatter_nick_lower_prefix_idx "
            "ON stream_sniper.chatter (lower(nick) text_pattern_ops)"
        )


def downgrade() -> None:
    _guard_online()
    # DROP INDEX CONCURRENTLY is also non-transactional. Qualify by the INDEX's
    # own schema (stream_sniper), not the table name.
    with op.get_context().autocommit_block():
        op.execute("DROP INDEX CONCURRENTLY IF EXISTS stream_sniper.chatter_nick_lower_prefix_idx")
