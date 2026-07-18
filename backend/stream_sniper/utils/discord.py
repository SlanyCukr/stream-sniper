"""Discord webhook delivery shared by analytics digests and tracking alerts."""

import requests


def deliver_discord(markdown: str, webhook_url: str) -> None:
    """POST a markdown payload to a Discord webhook, truncated to Discord's limit."""
    response = requests.post(webhook_url, json={"content": markdown[:2000]}, timeout=15)
    response.raise_for_status()
