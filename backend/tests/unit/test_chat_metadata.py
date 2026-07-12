"""
Unit tests for W5 collector chat metadata capture.

Covers:
- `extract_message_metadata` (chat_processor.py): pure extractor, parametrized over
  chat-downloader-shaped `line` dicts, including malformed input (never raises). Now also
  returns emote (name, twitch_id) pairs as the 4th element.
- `MessageHandler.handle_message`: metadata threaded into the 8-element insert tuple,
  default-arg path yields (None, None, None).
- `insert_message_db` (message_table_gateway.py): 8-column INSERT shape.
- `ChatProcessor.process_chat`: forwards the 3-tuple metadata to the handler and buffers
  emote (name -> id) pairs for the facade to drain.
"""

from datetime import datetime
from unittest.mock import Mock

import pytest

import stream_sniper.collector.message_handler as message_handler_module
from stream_sniper.collector.chat_processor import ChatProcessor, extract_message_metadata
from stream_sniper.collector.message_handler import MessageHandler
from stream_sniper.database.message_table_gateway import insert_message_db


class TestExtractMessageMetadata:
    """Parametrized coverage of extract_message_metadata (4-tuple with emote pairs)."""

    @pytest.mark.parametrize(
        "line, expected",
        [
            pytest.param(
                {
                    "author": {
                        "badges": [
                            {"name": "moderator", "version": "1"},
                            {"name": "subscriber", "version": "12"},
                        ],
                    },
                    "emotes": [
                        {"id": "25", "name": "Kappa"},
                        {"id": "305954156", "name": "PogChamp"},
                    ],
                },
                (True, "moderator/1,subscriber/12", 2, [("Kappa", "25"), ("PogChamp", "305954156")]),
                id="subscriber_with_emotes",
            ),
            pytest.param(
                {"author": {}, "emotes": []},
                (False, None, 0, []),  # known-zero emotes now (a real 0, not unknown-None)
                id="plain_viewer",
            ),
            pytest.param(
                {"author": {"badges": [{"name": "founder"}]}},
                (True, "founder/0", 0, []),
                id="founder_badge_default_version",
            ),
            pytest.param(
                {"author": {}},
                (False, None, 0, []),
                id="empty_author",
            ),
            pytest.param(
                {},
                (False, None, 0, []),
                id="missing_author_key",
            ),
            pytest.param(
                {"author": {"badges": ["just", "strings"]}},
                (False, None, 0, []),
                id="malformed_badges_not_dicts_never_raises",
            ),
            pytest.param(
                {"author": {}, "emotes": ["a", "b"]},
                (False, None, 0, []),  # malformed emote entries yield no pairs -> known-zero
                id="malformed_emotes_not_dicts_never_raises",
            ),
            pytest.param(
                {"author": {"badges": [{"version": "1"}, {"name": None}]}},
                (False, None, 0, []),
                id="malformed_badges_missing_name_never_raises",
            ),
            pytest.param(
                {"author": {}, "emotes": [{"name": "catJAM"}, {"id": "99"}]},
                (False, None, 1, [("catJAM", None)]),
                id="emote_without_id_keeps_name_id_none",
            ),
            pytest.param(
                "not-a-dict-line",
                (None, None, None, []),
                id="non_dict_line_hits_except_never_raises",
            ),
            pytest.param(
                None,
                (None, None, None, []),
                id="none_line_hits_except_never_raises",
            ),
        ],
    )
    def test_extract_message_metadata(self, line, expected):
        assert extract_message_metadata(line) == expected

    def test_explicit_is_subscriber_true_overrides_badge_absence(self):
        # If the source ever carries an explicit is_subscriber flag with no subscriber
        # badge, that explicit value wins over the badge-derived fallback.
        line = {"author": {"is_subscriber": True, "badges": [{"name": "moderator", "version": "1"}]}}
        assert extract_message_metadata(line) == (True, "moderator/1", 0, [])

    def test_never_raises_on_deeply_malformed_input(self):
        # Defensive smoke test: whatever garbage comes in, we get a 4-tuple back.
        for garbage in (123, [], {"author": 5}, {"author": {"badges": None}, "emotes": None}):
            result = extract_message_metadata(garbage)
            assert isinstance(result, tuple)
            assert len(result) == 4


class TestHandleMessageMetadata:
    """MessageHandler.handle_message threads metadata into the 8-element insert tuple."""

    @pytest.fixture
    def handler(self, monkeypatch):
        monkeypatch.setattr(message_handler_module, "insert_new_chatter_db", lambda nick: 1)
        monkeypatch.setattr(message_handler_module, "find_or_insert_message_text_id_db", lambda msg: 42)
        insert_fun = Mock()
        h = MessageHandler("creator_nick", insert_fun)
        h.known_chatters["viewer"] = 2
        return h, insert_fun

    def test_default_metadata_yields_none_triple(self, handler):
        h, insert_fun = handler
        ts = datetime(2024, 1, 1, 12, 0, 0)

        h.handle_message(ts, "viewer", "hello", 10)

        insert_fun.assert_called_once()
        (call_tuple,) = insert_fun.call_args[0]
        assert len(call_tuple) == 8
        assert call_tuple == (2, None, 10, 42, ts, None, None, None)

    def test_metadata_threaded_into_tuple_slots_5_to_7(self, handler):
        h, insert_fun = handler
        ts = datetime(2024, 1, 1, 12, 0, 0)

        h.handle_message(ts, "viewer", "hello", 10, metadata=(True, "subscriber/12", 3))

        (call_tuple,) = insert_fun.call_args[0]
        assert len(call_tuple) == 8
        assert call_tuple == (2, None, 10, 42, ts, True, "subscriber/12", 3)


class TestInsertMessageDb8Columns:
    """insert_message_db builds an 8-column, 8-placeholder INSERT in tuple order."""

    def test_sql_has_8_placeholders_and_columns_in_order(self):
        cursor = Mock()
        connection = Mock()
        items = [(1, None, 3, 4, "2024-01-01 00:00:00", True, "moderator/1", 2)]

        insert_message_db(items, cursor, connection)

        cursor.executemany.assert_called_once()
        sql, passed_items = cursor.executemany.call_args[0]

        assert sql.count("%s") == 8
        assert passed_items == items

        columns_str = sql.split("(", 1)[1].split(")", 1)[0]
        columns = [c.strip() for c in columns_str.split(",")]
        assert columns == [
            "chatter_id",
            "tagged_chatter_id",
            "stream_id",
            "message_text_id",
            "time",
            "is_subscriber",
            "badges",
            "emote_count",
        ]

        connection.commit.assert_called_once()


class TestProcessChatMetadataWiring:
    """ChatProcessor.process_chat forwards a 3-tuple metadata + buffers emote pairs."""

    def test_process_chat_passes_metadata_positionally(self):
        mock_handler = Mock()
        processor = ChatProcessor(creator_id=1, message_handling_fun=mock_handler)
        line = {
            "author": {"name": "viewer", "badges": [{"name": "subscriber", "version": "6"}]},
            "message": "hi",
            "timestamp": 1642287015000000,
        }

        processor.process_chat([line], 5)

        mock_handler.assert_called_once()
        args = mock_handler.call_args[0]
        assert len(args) == 5
        message_time, chatter_nick, message, stream_id, metadata = args
        assert isinstance(message_time, datetime)
        assert chatter_nick == "viewer"
        assert message == "hi"
        assert stream_id == 5
        assert metadata == (True, "subscriber/6", 0)

    def test_process_chat_buffers_emote_name_id_pairs(self):
        mock_handler = Mock()
        processor = ChatProcessor(creator_id=1, message_handling_fun=mock_handler)
        chat = [
            {
                "author": {"name": "a"},
                "message": "Kappa Kappa",
                "timestamp": 1,
                "emotes": [{"id": "25", "name": "Kappa"}],
            },
            {
                "author": {"name": "b"},
                "message": "catJAM PogChamp",
                "timestamp": 2,
                "emotes": [{"name": "catJAM"}, {"id": "88", "name": "PogChamp"}],
            },
        ]

        processor.process_chat(chat, 5)

        assert processor.batch_emotes == {"Kappa": "25", "catJAM": None, "PogChamp": "88"}

    def test_process_chat_resets_batch_emotes_between_batches(self):
        processor = ChatProcessor(creator_id=1, message_handling_fun=Mock())
        processor.process_chat(
            [{"author": {"name": "a"}, "message": "x", "timestamp": 1, "emotes": [{"id": "1", "name": "Old"}]}],
            5,
        )
        processor.process_chat(
            [{"author": {"name": "b"}, "message": "y", "timestamp": 2, "emotes": [{"id": "2", "name": "New"}]}],
            5,
        )
        assert processor.batch_emotes == {"New": "2"}

    def test_process_chat_missing_timestamp_still_raises(self):
        mock_handler = Mock()
        processor = ChatProcessor(creator_id=1, message_handling_fun=mock_handler)
        line = {"author": {"name": "viewer"}, "message": "hi"}  # no "timestamp"

        with pytest.raises(KeyError):
            processor.process_chat([line], 5)

        mock_handler.assert_not_called()
