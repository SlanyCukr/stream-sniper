from datetime import UTC, datetime
from typing import Callable, List

from tqdm import tqdm

from ..logging_config import get_logger


def extract_message_metadata(
    line: dict,
) -> tuple[bool | None, str | None, int | None, list[tuple[str, str | None]]]:
    """(is_subscriber, badges, emote_count, emote_pairs). Safe defaults on malformed input; never raises.

    emote_pairs is the list of (name, twitch_emote_id) seen in the line; the message-insert path uses
    only the first three fields (emote_count == len(emote_pairs) or None), while the collector facade
    consumes emote_pairs to grow the emote dictionary.
    """
    try:
        author = line.get("author") or {}
        raw_badges = author.get("badges") or []
        pairs = sorted(
            f"{b['name']}/{b.get('version', 0)}" for b in raw_badges if isinstance(b, dict) and b.get("name")
        )
        badges = ",".join(pairs) or None
        names = {p.split("/", 1)[0] for p in pairs}
        is_subscriber = author.get("is_subscriber")
        if is_subscriber is None:
            is_subscriber = bool(names & {"subscriber", "founder"})
        raw_emotes = line.get("emotes") or []
        emote_pairs = [(e["name"], e.get("id")) for e in raw_emotes if isinstance(e, dict) and e.get("name")]
        emote_count = len(emote_pairs) or None
        return is_subscriber, badges, emote_count, emote_pairs
    except Exception:
        get_logger(__name__).debug("metadata extraction failed for line", exc_info=True)
        return None, None, None, []


class ChatProcessor:
    def __init__(self, creator_id: int, message_handling_fun: Callable):
        self.creator_id = creator_id
        self.message_handling_fun = message_handling_fun
        self.logger = get_logger(__name__)
        # Emote (name -> twitch_id) pairs seen in the most recently processed batch; the facade
        # drains this after process_chat to grow the emote dictionary.
        self.batch_emotes: dict = {}

    def get_nicks(self, chat: List[str]):
        """¨
        :return:
        """
        self.logger.debug("Processing nicks.")

        chatter_nicks = []
        for line in chat:
            if line["author"] == {}:
                continue

            if "name" not in line["author"]:
                chatter_nicks.append("Unknown")
                continue

            chatter_nick = line["author"]["name"]

            chatter_nicks.append(chatter_nick)

        return list(set(chatter_nicks))

    def get_messages(self, chat: List[str]):
        """
        :return:
        """

        messages = []
        for line in chat:
            message = line["message"]
            messages.append(message)

        return list(set(messages))

    def process_chat(self, chat: List[dict], stream_id: int):
        self.logger.debug("Processing messages.")
        self.batch_emotes = {}
        for line in tqdm(chat):
            message_time = datetime.fromtimestamp(line["timestamp"] / 1000000, UTC)

            chatter_nick = line["author"].get("name", "Unknown")
            message = line["message"]
            is_subscriber, badges, emote_count, emote_pairs = extract_message_metadata(line)
            for name, provider_id in emote_pairs:
                self.batch_emotes[name] = provider_id

            self.message_handling_fun(
                message_time, chatter_nick, message, stream_id, (is_subscriber, badges, emote_count)
            )
