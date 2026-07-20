from dataclasses import dataclass
from datetime import UTC, datetime

from tqdm import tqdm  # type: ignore[import-untyped]

from ..badge_format import format_badge_pairs
from .twitch_archived_chat import ArchivedChatMessage


def extract_message_metadata(
    line: ArchivedChatMessage,
) -> tuple[bool, str | None, int, list[tuple[str, str | None]]]:
    """Return normalized subscriber, badge, and emote metadata.

    emote_pairs is the list of (name, twitch_emote_id) seen in the line; the message-insert path uses
    only the first three fields, while ``TwitchChatParser.parse_batch`` consumes emote_pairs to grow
    the emote dictionary. The Twitch client validates and normalizes required fields before this
    boundary.
    """
    author = line["author"]
    badges = format_badge_pairs((badge["name"], badge["version"]) for badge in author["badges"])
    emote_pairs: list[tuple[str, str | None]] = [(emote["name"], emote["id"]) for emote in line.get("emotes", [])]
    return author["is_subscriber"], badges, len(emote_pairs), emote_pairs


@dataclass(frozen=True)
class TwitchChatLine:
    source_message_id: str | None
    timestamp: datetime
    chatter_nick: str
    message: str
    is_subscriber: bool
    badges: str | None
    emote_count: int
    emotes: tuple[tuple[str, str | None], ...]


@dataclass(frozen=True)
class ParsedChatBatch:
    lines: tuple[TwitchChatLine, ...]
    unique_nicks: tuple[str, ...]
    unique_messages: tuple[str, ...]
    emotes: tuple[tuple[str, str | None], ...]


class TwitchChatParser:
    """Normalize third-party chat dictionaries into one explicit batch value."""

    def parse_batch(self, chat: list[ArchivedChatMessage]) -> ParsedChatBatch:
        lines: list[TwitchChatLine] = []
        emotes: dict[str, str | None] = {}
        for payload in tqdm(chat):
            author = payload["author"]
            message = payload["message"]
            timestamp = payload["timestamp"]
            if not isinstance(message, str):
                raise ValueError("Malformed Twitch chat message")
            if not isinstance(timestamp, (int, float)):
                raise ValueError("Malformed Twitch chat timestamp")
            is_subscriber, badges, emote_count, emote_pairs = extract_message_metadata(payload)
            emotes.update(emote_pairs)
            lines.append(
                TwitchChatLine(
                    source_message_id=payload.get("message_id"),
                    timestamp=datetime.fromtimestamp(timestamp / 1_000_000, UTC),
                    chatter_nick=author["name"] or "Unknown",
                    message=message,
                    is_subscriber=is_subscriber,
                    badges=badges,
                    emote_count=emote_count,
                    emotes=tuple(emote_pairs),
                )
            )
        return ParsedChatBatch(
            lines=tuple(lines),
            unique_nicks=tuple(sorted({line.chatter_nick for line in lines})),
            unique_messages=tuple(sorted({line.message for line in lines})),
            emotes=tuple(emotes.items()),
        )
