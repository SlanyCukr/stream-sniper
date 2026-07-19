"""Unit tests for the Discord webhook delivery helper.

Every caller of ``deliver_discord`` monkeypatches it out entirely, so these tests
exercise the real HTTP payload it builds against the ``requests`` library it
actually uses: the ``allowed_mentions: {"parse": []}`` mention-suppression
contract (security-relevant — untrusted stream titles / scene text flow into the
markdown body), line-boundary chunking across Discord's 2000-character cap, and
that HTTP errors raised by ``raise_for_status`` propagate to the caller.
"""

from unittest.mock import Mock, patch

import pytest
import requests

from stream_sniper.utils.discord import chunk_markdown, deliver_discord

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
def test_deliver_discord_chunks_long_content_across_messages(mock_post: Mock) -> None:
    """Over-limit digests are delivered in order as several posts, never truncated."""
    mock_post.return_value = Mock(raise_for_status=Mock())
    lines = [f"- line {i} " + "x" * 90 for i in range(50)]  # ~5000 chars total

    deliver_discord("\n".join(lines), WEBHOOK_URL)

    assert mock_post.call_count > 1
    sent = [call.kwargs["json"]["content"] for call in mock_post.call_args_list]
    assert all(len(chunk) <= 2000 for chunk in sent)
    # Nothing lost: rejoining the chunks reproduces every line, in order.
    assert "\n".join(sent) == "\n".join(lines)
    # Every message keeps the mention-suppression contract.
    assert all(
        call.kwargs["json"]["allowed_mentions"] == {"parse": []}
        for call in mock_post.call_args_list
    )


def test_chunk_markdown_splits_on_line_boundaries() -> None:
    lines = [f"line {i}" for i in range(5)]
    assert chunk_markdown("\n".join(lines), limit=14) == [
        "line 0\nline 1",
        "line 2\nline 3",
        "line 4",
    ]


def test_chunk_markdown_hard_splits_a_single_oversized_line() -> None:
    chunks = chunk_markdown("x" * 4500, limit=2000)
    assert [len(chunk) for chunk in chunks] == [2000, 2000, 500]
    assert "".join(chunks) == "x" * 4500


def test_chunk_markdown_short_content_is_one_chunk() -> None:
    assert chunk_markdown("short message") == ["short message"]
    assert chunk_markdown("") == []


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
