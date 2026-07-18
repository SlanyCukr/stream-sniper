"""Discord webhook delivery shared by analytics digests and tracking alerts."""

import requests


def deliver_discord(markdown: str, webhook_url: str) -> None:
    """POST a markdown payload to a Discord webhook, truncated to Discord's limit.

    ``allowed_mentions: {"parse": []}`` is mandatory: the content embeds untrusted
    text (stream titles, scene-event summaries), and without it a crafted
    ``<@user-id>`` / ``@everyone`` in a Twitch title would actually ping people.
    """
    response = requests.post(
        webhook_url,
        json={"content": markdown[:2000], "allowed_mentions": {"parse": []}},
        timeout=15,
    )
    response.raise_for_status()
