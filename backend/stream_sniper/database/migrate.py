"""Packaged Alembic entry point: `stream-sniper-migrate`.

Runs Alembic WITHOUT needing an alembic.ini, a source checkout, or a specific
cwd. The migrations directory ships inside the installed `stream_sniper` wheel,
so this works in the source-less prod container (no uv; only /app/.venv/bin on
PATH). alembic.ini is a dev-only convenience; this entry point ignores it and
sets script_location programmatically.

Examples:
    stream-sniper-migrate upgrade head
    stream-sniper-migrate stamp 0001
    stream-sniper-migrate current
    stream-sniper-migrate heads
"""

from __future__ import annotations

import sys
from pathlib import Path

from alembic.config import CommandLine, Config


def main(argv: list[str] | None = None) -> None:
    if argv is None:
        argv = sys.argv[1:]
    migrations_dir = str(Path(__file__).resolve().parent / "migrations")
    cli = CommandLine(prog="stream-sniper-migrate")
    options = cli.parser.parse_args(argv)
    if not hasattr(options, "cmd"):
        cli.parser.error("too few arguments")
        return
    # No file_=... -> config_file_name is None -> env.py skips fileConfig and
    # builds the engine from environment variables (same as connection_pool.py).
    cfg = Config(cmd_opts=options)
    cfg.set_main_option("script_location", migrations_dir)
    cli.run_cmd(cfg, options)


if __name__ == "__main__":
    main()
