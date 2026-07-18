"""Build and optionally deliver a deterministic scene digest to a Discord webhook."""

import argparse
import os
import sys
from collections.abc import Sequence

from stream_sniper.database.gateways.content.records import SceneEventRow

from ...database.core.connection_pool import database_entrypoint
from ...database.gateways.content.scene_event_table_gateway import select_scene_events_db
from ...utils.discord import deliver_discord


def format_digest(rows: Sequence[SceneEventRow], days: int) -> str:
    lines = [f"## Stream Sniper · {days}-day scene pulse"]
    if not rows:
        return "\n".join([*lines, "No notable captured events in this window."])
    for row in rows:
        creator = row.creator_display_name or row.creator_nick or "Scene"
        lines.append(f"- **{row.title}** — {row.summary} ({creator}, {row.occurred_at[:10]})")
    return "\n".join(lines)


def build_digest(days: int = 7, limit: int = 20) -> str:
    rows, _ = select_scene_events_db(days, None, None, limit, 0)
    return format_digest(rows, days)


@database_entrypoint
def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or deliver the Stream Sniper scene digest")
    parser.add_argument("--days", type=int, default=7, choices=range(1, 31))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--send", action="store_true", help="Deliver to the configured Discord webhook")
    # The webhook contract is declared once at this CLI boundary: an explicit
    # flag wins, with the SCENE_DIGEST_WEBHOOK_URL environment variable as the
    # deployment default.
    parser.add_argument(
        "--webhook-url",
        default=os.getenv("SCENE_DIGEST_WEBHOOK_URL"),
        help="Discord webhook destination (default: $SCENE_DIGEST_WEBHOOK_URL)",
    )
    args = parser.parse_args()
    digest = build_digest(args.days, max(1, min(args.limit, 50)))
    if not args.send:
        print(digest)
        return
    if not args.webhook_url:
        print("--webhook-url (or SCENE_DIGEST_WEBHOOK_URL) is required with --send", file=sys.stderr)
        raise SystemExit(2)
    deliver_discord(digest, args.webhook_url)
    print("Scene digest delivered.")


if __name__ == "__main__":
    main()
