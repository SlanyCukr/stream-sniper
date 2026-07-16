"""Project-owned Twitch GraphQL client for archived VOD chat."""

import time
from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Literal, NotRequired, TypedDict, cast

import requests

from ...logging_config import get_logger

_GQL_URL = "https://gql.twitch.tv/gql"
_PUBLIC_CLIENT_ID = "kd1unb4b3q4t58fwlpcbzcbnm76a8fp"
_COMMENTS_OPERATION = "VideoCommentsByOffsetOrCursor"
_COMMENTS_HASH = "b70a3591ff0f4e0313d126c6a1502d79a1c02baebb288227c582044aa76adf6a"
_REQUEST_TIMEOUT_SECONDS = 30.0
_NULL_COMMENTS_RETRIES = 4
_BACKOFF_BASE_SECONDS = 1.5


class ArchivedChatBadge(TypedDict):
    name: str
    version: str


class ArchivedChatEmote(TypedDict):
    id: str
    name: str


class ArchivedChatAuthor(TypedDict):
    id: str | None
    name: str | None
    display_name: str | None
    badges: list[ArchivedChatBadge]
    is_subscriber: bool


class ArchivedChatMessage(TypedDict):
    message_id: str | None
    timestamp: int
    time_in_seconds: int | float | None
    author: ArchivedChatAuthor
    message: str
    message_type: Literal["text_message"]
    emotes: NotRequired[list[ArchivedChatEmote]]


JsonScalar = str | int | float | bool | None
JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
PostJson = Callable[[str, JsonValue, Mapping[str, str], float], object]


class ArchivedChatError(RuntimeError):
    """Twitch archived-chat request or response failure."""


def _post_json(url: str, payload: JsonValue, headers: Mapping[str, str], timeout: float) -> object:
    response = requests.post(url, json=payload, headers=headers, timeout=timeout)
    response.raise_for_status()
    return cast(object, response.json())


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, dict):
        raise ArchivedChatError(f"Malformed Twitch archived-chat {label}")
    return cast(Mapping[str, object], value)


def _sequence(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ArchivedChatError(f"Malformed Twitch archived-chat {label}")
    return cast(list[object], value)


def _timestamp_microseconds(value: object) -> int:
    if not isinstance(value, str):
        raise ArchivedChatError("Archived-chat message has no creation timestamp")
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp() * 1_000_000)


def _normalize_comment(node_value: object) -> ArchivedChatMessage:
    node = _mapping(node_value, "comment")
    commenter_value = node.get("commenter")
    commenter = _mapping(commenter_value, "commenter") if commenter_value is not None else {}
    message = _mapping(node.get("message"), "message")
    fragments = _sequence(message.get("fragments"), "message fragments")

    text_parts: list[str] = []
    emotes: list[ArchivedChatEmote] = []
    for fragment_value in fragments:
        fragment = _mapping(fragment_value, "message fragment")
        text = fragment.get("text")
        if not isinstance(text, str):
            raise ArchivedChatError("Archived-chat fragment has no text")
        text_parts.append(text)
        emote_value = fragment.get("emote")
        if emote_value is not None:
            emote = _mapping(emote_value, "emote")
            emote_id = emote.get("emoteID")
            if isinstance(emote_id, str):
                emotes.append({"id": emote_id, "name": text})

    badges: list[ArchivedChatBadge] = []
    badges_value = message.get("userBadges") or []
    for badge_value in _sequence(badges_value, "user badges"):
        badge = _mapping(badge_value, "user badge")
        name, version = badge.get("setID"), badge.get("version")
        if isinstance(name, str) and isinstance(version, str):
            badges.append({"name": name, "version": version})

    author_id = commenter.get("id")
    author_name = commenter.get("login")
    display_name = commenter.get("displayName")
    author: ArchivedChatAuthor = {
        "id": author_id if isinstance(author_id, str) else None,
        "name": author_name if isinstance(author_name, str) else None,
        "display_name": display_name if isinstance(display_name, str) else None,
        "badges": badges,
        "is_subscriber": any(badge["name"] in {"subscriber", "founder"} for badge in badges),
    }
    message_id = node.get("id")
    offset = node.get("contentOffsetSeconds")
    result: ArchivedChatMessage = {
        "message_id": message_id if isinstance(message_id, str) else None,
        "timestamp": _timestamp_microseconds(node.get("createdAt")),
        "time_in_seconds": offset if isinstance(offset, (int, float)) else None,
        "author": author,
        "message": "".join(text_parts),
        "message_type": "text_message",
    }
    if emotes:
        result["emotes"] = emotes
    return result


@dataclass(frozen=True)
class _CommentsPage:
    messages: tuple[ArchivedChatMessage, ...]
    cursor: str | None
    has_next: bool


class TwitchArchivedChatClient:
    """Fetch and normalize Twitch VOD comments without third-party runtime patches."""

    def __init__(
        self,
        post_json: PostJson = _post_json,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._post_json = post_json
        self._sleep = sleep
        self._logger = get_logger(__name__)

    def open_messages(self, twitch_vod_id: int) -> Iterator[ArchivedChatMessage]:
        """Validate the first page eagerly, then return a lazy full-chat iterator."""
        first_page = self._fetch_page(twitch_vod_id, cursor=None)
        return self._iterate_pages(twitch_vod_id, first_page)

    def _iterate_pages(self, twitch_vod_id: int, page: _CommentsPage) -> Iterator[ArchivedChatMessage]:
        while True:
            yield from page.messages
            if not page.has_next:
                return
            if not page.cursor:
                raise ArchivedChatError("Twitch archived-chat page has no continuation cursor")
            page = self._fetch_page(twitch_vod_id, cursor=page.cursor)

    def _fetch_page(self, twitch_vod_id: int, cursor: str | None) -> _CommentsPage:
        variables: dict[str, JsonValue] = {"videoID": str(twitch_vod_id)}
        if cursor is None:
            variables["contentOffsetSeconds"] = 0
        else:
            variables["cursor"] = cursor
        payload: JsonValue = [
            {
                "operationName": _COMMENTS_OPERATION,
                "variables": variables,
                "extensions": {"persistedQuery": {"version": 1, "sha256Hash": _COMMENTS_HASH}},
            }
        ]
        headers = {"Client-ID": _PUBLIC_CLIENT_ID, "Content-Type": "application/json"}

        for attempt in range(_NULL_COMMENTS_RETRIES + 1):
            try:
                response = self._post_json(_GQL_URL, payload, headers, _REQUEST_TIMEOUT_SECONDS)
                page = self._parse_page(response)
            except Exception as exc:
                if attempt == _NULL_COMMENTS_RETRIES:
                    raise ArchivedChatError(f"Failed to fetch Twitch archived chat for VOD {twitch_vod_id}") from exc
                self._backoff(twitch_vod_id, attempt, "request failed")
                continue
            if page is not None:
                return page
            if attempt < _NULL_COMMENTS_RETRIES:
                self._backoff(twitch_vod_id, attempt, "comments were missing")

        return _CommentsPage(messages=(), cursor=None, has_next=False)

    def _backoff(self, twitch_vod_id: int, attempt: int, reason: str) -> None:
        delay = _BACKOFF_BASE_SECONDS * (2**attempt)
        self._logger.warning(
            "Twitch VOD %s archived-chat %s; retrying in %.1fs (%s/%s)",
            twitch_vod_id,
            reason,
            delay,
            attempt + 1,
            _NULL_COMMENTS_RETRIES,
        )
        self._sleep(delay)

    @staticmethod
    def _parse_page(response: object) -> _CommentsPage | None:
        entries = _sequence(response, "response")
        if not entries:
            raise ArchivedChatError("Empty Twitch archived-chat response")
        root = _mapping(entries[0], "response entry")
        if root.get("errors"):
            raise ArchivedChatError("Twitch archived-chat GraphQL error")
        data = _mapping(root.get("data"), "response data")
        video = _mapping(data.get("video"), "video")
        comments_value = video.get("comments")
        if comments_value is None:
            return None
        comments = _mapping(comments_value, "comments")
        edges = _sequence(comments.get("edges") or [], "comment edges")
        messages: list[ArchivedChatMessage] = []
        cursor: str | None = None
        for edge_value in edges:
            edge = _mapping(edge_value, "comment edge")
            edge_cursor = edge.get("cursor")
            if isinstance(edge_cursor, str):
                cursor = edge_cursor
            node = edge.get("node")
            if node is not None:
                messages.append(_normalize_comment(node))
        page_info = _mapping(comments.get("pageInfo"), "page info")
        return _CommentsPage(
            messages=tuple(messages),
            cursor=cursor,
            has_next=page_info.get("hasNextPage") is True,
        )
