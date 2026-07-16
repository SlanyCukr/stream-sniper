"""Build and optionally deliver a deterministic scene digest to a Discord webhook."""

import argparse
import os
import sys
from collections.abc import Sequence

import requests

from stream_sniper.database.gateways.content.records import SceneEventRow

from ...database.core.connection_pool import database_entrypoint
from ...database.gateways.content.scene_event_table_gateway import select_scene_events_db


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


def deliver_discord(markdown: str, webhook_url: str) -> None:
    response = requests.post(webhook_url, json={"content": markdown[:2000]}, timeout=15)
    response.raise_for_status()


@database_entrypoint
def main() -> None:
    parser = argparse.ArgumentParser(description="Preview or deliver the Stream Sniper scene digest")
    parser.add_argument("--days", type=int, default=7, choices=range(1, 31))
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--send", action="store_true", help="Deliver to SCENE_DIGEST_WEBHOOK_URL")
    args = parser.parse_args()
    digest = build_digest(args.days, max(1, min(args.limit, 50)))
    if not args.send:
        print(digest)
        return
    webhook = os.getenv("SCENE_DIGEST_WEBHOOK_URL")
    if not webhook:
        print("SCENE_DIGEST_WEBHOOK_URL is required with --send", file=sys.stderr)
        raise SystemExit(2)
    deliver_discord(digest, webhook)
    print("Scene digest delivered.")


if __name__ == "__main__":
    main()
