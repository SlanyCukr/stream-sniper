"""Alembic environment for Stream Sniper.

Migrations are HAND-WRITTEN raw SQL (op.execute / op.create_*). There are no ORM
models and no autogenerate; target_metadata is None.

The database URL and schema match the POSTGRES_* contract consumed by API
configuration used by executable database runtimes:
  * load_dotenv() first,
  * one POSTGRES_* environment contract,
  * port default 5432,
  * schema `stream_sniper` applied via libpq search_path (same as the app), and
    alembic_version kept in that schema via version_table_schema.

CRITICAL ordering note: because version_table_schema="stream_sniper", Alembic
emits `CREATE TABLE stream_sniper.alembic_version` BEFORE running revision 0001's
upgrade(). On a FRESH/empty DB the schema does not exist yet, so we MUST create it
here first, on a SEPARATE short-lived transaction, before opening the migration
connection. Doing it on the migration connection (before context.configure) would
corrupt transaction_per_migration and break 0002's autocommit_block(); doing it in
0001.upgrade() is too late. It is idempotent (harmless on prod, whose schema
already exists).
"""

from __future__ import annotations

import os
from logging.config import fileConfig

from alembic import context
from dotenv import load_dotenv
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import URL

# Alembic Config object. config_file_name is None when invoked via the packaged
# `stream-sniper-migrate` entry point (no ini); non-None under `uv run alembic`.
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Hand-written migrations -> no autogenerate metadata.
target_metadata = None

SCHEMA = "stream_sniper"


def _db_env(name: str, default: str | None = None) -> str:
    """Read the same required POSTGRES_* contract as the application."""
    value = os.environ.get(name) or default
    if value is None:
        raise RuntimeError(f"Database configuration missing: set {name} in the environment")
    return value


def _build_url() -> URL:
    # Mirror the app: read .env before touching os.environ. load_dotenv() does
    # NOT override already-exported vars, so explicit env wins (used by CI/verify).
    load_dotenv()
    # URL.create() takes RAW components — no manual URL-encoding of the password;
    # SQLAlchemy hands username/password/host/port/database to psycopg2 verbatim,
    # so special characters (@ : / # ? % space) need zero escaping.
    return URL.create(
        drivername="postgresql+psycopg2",
        username=_db_env("POSTGRES_USER"),
        password=_db_env("POSTGRES_PASSWORD"),
        host=_db_env("POSTGRES_HOST"),
        database=_db_env("POSTGRES_DB"),
        port=int(_db_env("POSTGRES_PORT", "5432")),
    )


def _connect_args() -> dict:
    # Identical to connection_pool.py's psycopg2 kwargs: search_path via libpq
    # `options`, plus connect_timeout. NO sslmode (libpq default `prefer`), and
    # NO statement_timeout (must never abort CREATE INDEX CONCURRENTLY).
    return {
        "options": f"-c search_path={SCHEMA}",
        "connect_timeout": int(os.environ.get("DB_CONNECT_TIMEOUT", "10")),
    }


def run_migrations_offline() -> None:
    """--sql mode: emit SQL with no DB connection.

    No connection means libpq `options` can't set search_path, so migrations MUST
    schema-qualify every object (they do). We emit CREATE SCHEMA FIRST so the
    generated script is applicable to a genuinely fresh DB before the
    schema-qualified alembic_version table is created. version_table_schema
    qualifies the alembic_version bookkeeping. The CONCURRENTLY index (0002) is
    NOT meant for offline and refuses to run there (see 0002).
    """
    context.configure(
        url=_build_url(),
        target_metadata=target_metadata,
        version_table_schema=SCHEMA,
        include_schemas=True,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        # Emit before the version table / any migration so offline --sql output is
        # self-sufficient on a fresh DB. Parity with the online bootstrap below.
        context.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(
        _build_url(),
        poolclass=pool.NullPool,  # short-lived migration engine
        connect_args=_connect_args(),  # search_path=stream_sniper, like the app
    )

    # STEP 1 — ensure the schema exists on a SEPARATE, fully-committed transaction,
    # BEFORE Alembic touches (and schema-qualifies) alembic_version. Must NOT be on
    # the migration connection, or transaction_per_migration / autocommit_block break.
    with connectable.begin() as bootstrap:
        bootstrap.exec_driver_sql(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # STEP 2 — run migrations on a fresh connection.
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table_schema=SCHEMA,  # alembic_version lives in stream_sniper
            include_schemas=True,  # harmless now; ready if autogenerate is ever added
            transaction_per_migration=True,  # each migration in its own tx; keeps
            # autocommit_block() (CONCURRENTLY) clean
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
