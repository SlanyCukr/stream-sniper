"""Unit tests for the Discord webhook delivery helper.

Every caller of ``deliver_discord`` monkeypatches it out entirely, so these tests
exercise the real HTTP payload it builds against the ``requests`` library it
actually uses: the ``allowed_mentions: {"parse": []}`` mention-suppression
contract (security-relevant — untrusted stream titles / scene text flow into the
markdown body), the 2000-character Discord content truncation, and that HTTP
errors raised by ``raise_for_status`` propagate to the caller.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from stream_sniper.utils.discord import deliver_discord

WEBHOOK_URL = "https://discord.com/api/webhooks/123/abc"


@patch("stream_sniper.utils.discord.requests.post")
def test_deliver_discord_suppresses_mentions(mock_post: Mock) -> None:
    """The payload must always disable mention parsing to prevent ping injection."""
    mock_post.return_value = Mock(raise_for_status=Mock())

    deliver_discord("hello <@everyone>", WEBHOOK_URL)

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["allowed_mentions"] == {"parse": []}


@patch("stream_sniper.utils.discord.requests.post")
def test_deliver_discord_posts_to_webhook_url_with_timeout(mock_post: Mock) -> None:
    mock_post.return_value = Mock(raise_for_status=Mock())

    deliver_discord("hello", WEBHOOK_URL)

    args, kwargs = mock_post.call_args
    assert args[0] == WEBHOOK_URL
    assert kwargs["timeout"] == 15


@patch("stream_sniper.utils.discord.requests.post")
def test_deliver_discord_truncates_content_to_2000_chars(mock_post: Mock) -> None:
    mock_post.return_value = Mock(raise_for_status=Mock())
    long_markdown = "x" * 5000

    deliver_discord(long_markdown, WEBHOOK_URL)

    _, kwargs = mock_post.call_args
    sent_content = kwargs["json"]["content"]
    assert len(sent_content) == 2000
    assert sent_content == "x" * 2000


@patch("stream_sniper.utils.discord.requests.post")
def test_deliver_discord_short_content_is_not_padded_or_truncated(mock_post: Mock) -> None:
    mock_post.return_value = Mock(raise_for_status=Mock())

    deliver_discord("short message", WEBHOOK_URL)

    _, kwargs = mock_post.call_args
    assert kwargs["json"]["content"] == "short message"


@patch("stream_sniper.utils.discord.requests.post")
def test_deliver_discord_propagates_http_errors(mock_post: Mock) -> None:
    response = Mock()
    response.raise_for_status.side_effect = requests.HTTPError("500 Server Error")
    mock_post.return_value = response

    with pytest.raises(requests.HTTPError):
        deliver_discord("hello", WEBHOOK_URL)


@patch("stream_sniper.utils.discord.requests.post")
def test_deliver_discord_propagates_connection_errors(mock_post: Mock) -> None:
    mock_post.side_effect = requests.ConnectionError("connection refused")

    with pytest.raises(requests.ConnectionError):
        deliver_discord("hello", WEBHOOK_URL)
