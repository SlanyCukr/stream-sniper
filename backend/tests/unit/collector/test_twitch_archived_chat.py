"""Contract tests for the project-owned Twitch archived-chat client."""

from collections.abc import Mapping

import pytest

from stream_sniper.collector.archived.twitch_archived_chat import ArchivedChatError, TwitchArchivedChatClient


def _comment(message_id: str, text: str, *, emote_id: str | None = None):
    fragment = {"text": text, "emote": {"emoteID": emote_id, "id": "0-4"} if emote_id else None}
    return {
        "id": message_id,
        "createdAt": "2024-01-15T20:00:00Z",
        "contentOffsetSeconds": 12.5,
        "commenter": {"id": "7", "login": "viewer", "displayName": "Viewer"},
        "message": {
            "fragments": [fragment],
            "userBadges": [{"setID": "subscriber", "version": "6"}],
        },
    }


def _page(nodes, *, has_next=False):
    return [
        {
            "data": {
                "video": {
                    "comments": {
                        "edges": [
                            {"cursor": f"cursor-{index}", "node": node} for index, node in enumerate(nodes, start=1)
                        ],
                        "pageInfo": {"hasNextPage": has_next},
                    }
                }
            }
        }
    ]


def test_normalizes_and_paginates_archived_comments():
    responses = iter([_page([_comment("m1", "Kappa", emote_id="25")], has_next=True), _page([_comment("m2", "hi")])])
    calls: list[object] = []

    def post_json(_url: str, payload: object, _headers: Mapping[str, str], _timeout: float) -> object:
        calls.append(payload)
        return next(responses)

    messages = list(TwitchArchivedChatClient(post_json=post_json, sleep=lambda _delay: None).open_messages(123))

    assert [message["message_id"] for message in messages] == ["m1", "m2"]
    assert messages[0]["message"] == "Kappa"
    assert messages[0]["emotes"] == [{"id": "25", "name": "Kappa"}]
    assert messages[0]["author"]["name"] == "viewer"
    assert messages[0]["author"]["is_subscriber"] is True
    assert messages[0]["timestamp"] == 1_705_348_800_000_000
    assert len(calls) == 2
    assert calls[0][0]["variables"] == {"videoID": "123", "contentOffsetSeconds": 0}
    assert calls[1][0]["variables"] == {"videoID": "123", "cursor": "cursor-1"}


def test_retries_missing_comments_without_silently_truncating():
    responses = iter([None, None, _page([_comment("m1", "recovered")])])
    delays: list[float] = []

    def post_json(_url: str, _payload: object, _headers: Mapping[str, str], _timeout: float) -> object:
        response = next(responses)
        if response is None:
            return [{"data": {"video": {"comments": None}}}]
        return response

    messages = list(TwitchArchivedChatClient(post_json=post_json, sleep=delays.append).open_messages(123))

    assert [message["message"] for message in messages] == ["recovered"]
    assert delays == [1.5, 3.0]


def test_first_page_failure_is_eager_and_wrapped():
    def post_json(_url: str, _payload: object, _headers: Mapping[str, str], _timeout: float) -> object:
        raise OSError("network down")

    with pytest.raises(ArchivedChatError, match="VOD 123"):
        TwitchArchivedChatClient(post_json=post_json, sleep=lambda _delay: None).open_messages(123)


def test_next_page_without_cursor_fails_instead_of_looping():
    response = [{"data": {"video": {"comments": {"edges": [], "pageInfo": {"hasNextPage": True}}}}}]
    client = TwitchArchivedChatClient(post_json=lambda *_args: response, sleep=lambda _delay: None)

    with pytest.raises(ArchivedChatError, match="continuation cursor"):
        list(client.open_messages(123))
