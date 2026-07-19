"""Discord webhook delivery shared by analytics digests and tracking alerts."""

import requests

# Discord's hard cap on a single message's ``content`` field.
DISCORD_CONTENT_LIMIT = 2000


def chunk_markdown(markdown: str, limit: int = DISCORD_CONTENT_LIMIT) -> list[str]:
    """Split markdown into <=limit chunks, breaking on line boundaries.

    Long digests are delivered as several sequential messages instead of being
    silently truncated. Lines are packed greedily; a single line longer than the
    limit (no newline to break on) is hard-split so no chunk can exceed it.
    Blank-only chunks are dropped.
    """
    chunks: list[str] = []
    current = ""
    for line in markdown.split("\n"):
        # Hard-split a pathological single line that alone exceeds the limit.
        while len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            chunks.append(line[:limit])
            line = line[limit:]
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            chunks.append(current)
            current = line
        else:
            current = candidate
    if current.strip():
        chunks.append(current)
    return [chunk for chunk in chunks if chunk.strip()]


def deliver_discord(markdown: str, webhook_url: str) -> None:
    """POST a markdown payload to a Discord webhook, chunked to Discord's limit.

    Content over 2000 characters is split on line boundaries and delivered as
    sequential messages (order preserved) rather than truncated.

    ``allowed_mentions: {"parse": []}`` is mandatory: the content embeds untrusted
    text (stream titles, scene-event summaries), and without it a crafted
    ``<@user-id>`` / ``@everyone`` in a Twitch title would actually ping people.
    """
    for chunk in chunk_markdown(markdown):
        response = requests.post(
            webhook_url,
            json={"content": chunk, "allowed_mentions": {"parse": []}},
            timeout=15,
        )
        response.raise_for_status()
