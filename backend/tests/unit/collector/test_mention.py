"""The @mention -> chatter-nick token is one shared rule for both ingestion paths.

Guards the unification of the archived (VOD) and live (IRC) taggers: the same message
text must resolve to the same tagged chatter regardless of which collector saw it,
including the trailing-punctuation case that used to diverge.
"""

from datetime import UTC, datetime

from stream_sniper.collector.archived.chat_parser import TwitchChatParser
from stream_sniper.collector.archived.message_rows import build_message_rows, collect_mention_nicks
from stream_sniper.collector.live.live_message_sink import LiveMessageSink
from stream_sniper.collector.mention import mention_token


class TestMentionToken:
    def test_lowercased_word_after_first_at(self):
        assert mention_token("hey @Creator how are you") == "creator"

    def test_strips_trailing_sentence_punctuation(self):
        for text in ("hey @creator.", "hey @creator!", "hey @creator,", "hey @creator?", "hey @creator:;"):
            assert mention_token(text) == "creator", text

    def test_keeps_inner_punctuation(self):
        # Only *trailing* punctuation is stripped; a nick-internal underscore stays.
        assert mention_token("gg @cool_guy!") == "cool_guy"

    def test_none_without_mention(self):
        assert mention_token("no mention here") is None

    def test_none_when_only_punctuation_after_at(self):
        assert mention_token("what @!!! now") is None


def _author(name):
    return {"id": None, "name": name, "display_name": name, "badges": [], "is_subscriber": False}


class TestBothPathsAgreeOnPunctuation:
    """The archived and live taggers resolve "@creator." to the same chatter id."""

    def test_archived_path_strips_punctuation(self):
        batch = TwitchChatParser().parse_batch(
            [
                {
                    "author": _author("viewer"),
                    "message_id": "c-1",
                    "message": "yo @creator!",
                    "timestamp": 1_642_287_015_000_000,
                    "emotes": [],
                }
            ]
        )
        assert collect_mention_nicks(batch) == ["creator"]

        rows = build_message_rows(
            batch,
            stream_id=10,
            chatter_ids={"viewer": 2, "creator": 1},
            message_ids={"yo @creator!": 42},
        ).rows
        # tagged_chatter_id (row index 1) resolves to creator despite the trailing "!".
        assert rows[0][1] == 1

    def test_live_path_strips_punctuation(self):
        sink = LiveMessageSink(buffer_size=10)
        sink._chatters = {"creator": 1}
        assert sink._tagged_chatter_id("yo @creator!") == 1
        assert sink._tagged_chatter_id("yo @creator") == 1

    def test_both_paths_produce_identical_tagged_id(self):
        text = "spam @creator."
        batch = TwitchChatParser().parse_batch(
            [
                {
                    "author": _author("viewer"),
                    "message_id": "c-2",
                    "message": text,
                    "timestamp": 1_642_287_015_000_000,
                    "emotes": [],
                }
            ]
        )
        archived_tagged = build_message_rows(
            batch,
            stream_id=1,
            chatter_ids={"viewer": 2, "creator": 7},
            message_ids={text: 99},
        ).rows[0][1]

        sink = LiveMessageSink(buffer_size=10)
        sink._chatters = {"creator": 7}
        live_tagged = sink._tagged_chatter_id(text)

        assert archived_tagged == live_tagged == 7


def test_archived_row_timestamp_shape_unchanged():
    # Sanity: unrelated row fields still build (guards the import refactor).
    batch = TwitchChatParser().parse_batch(
        [
            {
                "author": _author("viewer"),
                "message_id": "c-3",
                "message": "plain message",
                "timestamp": 1_642_287_015_000_000,
                "emotes": [],
            }
        ]
    )
    row = build_message_rows(batch, stream_id=1, chatter_ids={"viewer": 2}, message_ids={"plain message": 5}).rows[0]
    assert row[1] is None  # no mention -> no tagged chatter
    assert row[4] == datetime.fromtimestamp(1_642_287_015, UTC)
