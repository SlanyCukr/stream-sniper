"""Build and optionally deliver a deterministic scene-intelligence digest to Discord.

The digest is a multi-section markdown report assembled from the same rollup
gateways the dashboard reads (scene events, trending velocity, chatter rankings,
highlights). Sections with no data are omitted rather than rendered empty, so a
quiet week produces a short digest, not a wall of placeholder headers. Delivery
chunks across multiple Discord messages when the report exceeds the 2000-char cap
(see ``utils.discord``).
"""

import argparse
import os
import sys
from collections.abc import Sequence

from stream_sniper.database.gateways.content.records import SceneEventRow

from ...database.core.connection_pool import database_entrypoint
from ...database.gateways.analytics.scene_trends_gateway import (
    TrendingCopypastaRow,
    TrendingEmoteRow,
    select_trending_copypastas_db,
    select_trending_emotes_db,
)
from ...database.gateways.content.scene_event_table_gateway import select_scene_events_db
from ...database.gateways.content.scene_highlights_gateway import (
    SceneHighlightRow,
    select_scene_highlights_db,
)
from ...database.gateways.creators.scene_chatter_rankings_gateway import (
    SceneChatterRankRow,
    select_scene_chatter_rankings_db,
)
from ...utils.discord import deliver_discord

SITE_BASE = "https://stream-sniper.slanycukr.com"

# Per-section row budgets: the digest is an inbox, not an export.
_TRENDING_LIMIT = 5
_CHATTERS_LIMIT = 5
_HIGHLIGHTS_LIMIT = 3


def _delta_label(current: int, prior: int) -> str:
    """Discord-friendly velocity marker mirroring the API's trend policy.

    prior == 0 is "new" (no baseline — a percent would be misleading), otherwise a
    sign-aware whole percent vs the prior window; equal usage reads "steady".
    """
    if prior == 0:
        return "new"
    if current == prior:
        return "steady"
    pct = round(100 * (current - prior) / prior)
    return f"▲ +{pct}%" if pct > 0 else f"▼ {pct}%"


def _clip(text: str, max_len: int = 80) -> str:
    """One-line preview of untrusted chat text: newlines flattened, clipped with an ellipsis."""
    flat = " ".join(text.split())
    return flat if len(flat) <= max_len else f"{flat[: max_len - 1].rstrip()}…"


def format_digest(rows: Sequence[SceneEventRow], days: int) -> str:
    """Header + notable-events section (the original digest core, kept stable)."""
    lines = [f"## Stream Sniper · {days}-day scene pulse"]
    if not rows:
        return "\n".join([*lines, "No notable captured events in this window."])
    for row in rows:
        creator = row.creator_display_name or row.creator_nick or "Scene"
        lines.append(f"- **{row.title}** — {row.summary} ({creator}, {row.occurred_at[:10]})")
    return "\n".join(lines)


def format_trending_copypastas(rows: Sequence[TrendingCopypastaRow]) -> str | None:
    """Rising copypastas with velocity vs the prior window; None when nothing trends."""
    if not rows:
        return None
    lines = ["### Rising copypastas"]
    for row in rows:
        lines.append(
            f'- "{_clip(row.text)}" — {row.current_usage} uses'
            f" ({_delta_label(row.current_usage, row.prior_usage)}), {row.creator_count} channels"
        )
    return "\n".join(lines)


def format_trending_emotes(rows: Sequence[TrendingEmoteRow]) -> str | None:
    """Rising emotes with velocity and channel spread; None when nothing trends."""
    if not rows:
        return None
    lines = ["### Rising emotes"]
    for row in rows:
        lines.append(
            f"- **{row.name}** ({row.source}) — {row.current_usage} uses"
            f" ({_delta_label(row.current_usage, row.prior_usage)}), {row.creator_count} channels"
        )
    return "\n".join(lines)


def format_top_chatters(rows: Sequence[SceneChatterRankRow]) -> str | None:
    """The window's most active chatters with their home channel; None when the window is empty."""
    if not rows:
        return None
    lines = ["### Most active chatters"]
    for rank, row in enumerate(rows, start=1):
        home = row.home_creator_display_name or row.home_creator_nick
        home_part = f", home: {home}" if home else ""
        lines.append(
            f"{rank}. **{row.nick}** — {row.total_messages} msgs"
            f" across {row.creators_visited} channels{home_part}"
        )
    return "\n".join(lines)


def format_highlights(rows: Sequence[SceneHighlightRow]) -> str | None:
    """Hype-ranked moments with dashboard deep links; None when no moments persisted."""
    if not rows:
        return None
    lines = ["### Biggest moments"]
    for row in rows:
        creator = row.creator_display_name or row.creator_nick
        ratio_part = f" ({row.ratio:g}× baseline)" if row.ratio is not None else ""
        phrase = row.top_phrases[0]["phrase"] if row.top_phrases else "chat spike"
        lines.append(
            f'- **{creator}** — "{_clip(phrase, 48)}", {row.message_count} msgs'
            f"{ratio_part} → {SITE_BASE}/stream/{row.stream_id}"
        )
    return "\n".join(lines)


def build_digest(days: int = 7, limit: int = 20) -> str:
    """Assemble the full scene-intelligence digest for the trailing window.

    Sections in fixed order: notable events (with header), rising copypastas,
    rising emotes, most active chatters, biggest moments. Empty sections are
    dropped entirely.
    """
    events, _ = select_scene_events_db(days, None, None, limit, 0)
    copypastas = select_trending_copypastas_db(days, None, _TRENDING_LIMIT)
    emotes = select_trending_emotes_db(days, None, _TRENDING_LIMIT)
    chatters, _ = select_scene_chatter_rankings_db(days, _CHATTERS_LIMIT, 0)
    highlights, _ = select_scene_highlights_db(days, None, "hype", _HIGHLIGHTS_LIMIT, 0)

    sections = [
        format_digest(events, days),
        format_trending_copypastas(copypastas),
        format_trending_emotes(emotes),
        format_top_chatters(chatters),
        format_highlights(highlights),
    ]
    return "\n\n".join(section for section in sections if section is not None)


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
