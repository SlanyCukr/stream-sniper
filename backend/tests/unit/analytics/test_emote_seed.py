"""Unit tests for BTTV emote-dictionary seeding (provider_id validation; gateway mocked)."""

from unittest.mock import patch

from stream_sniper.analytics.rollups import emote_seed


class TestValidBttvId:
    def test_accepts_hex_ids_in_range(self):
        assert emote_seed._valid_bttv_id("60ca186ef8b3f62601c3eb1d") == "60ca186ef8b3f62601c3eb1d"
        assert emote_seed._valid_bttv_id("aaaaaaaaaaaa") == "aaaaaaaaaaaa"  # 12 chars, lower bound

    def test_rejects_malformed_ids(self):
        # Too short, uppercase/non-hex, path-injection, and None all collapse to name-only (None).
        assert emote_seed._valid_bttv_id("abc") is None
        assert emote_seed._valid_bttv_id("../../etc/passwd") is None
        assert emote_seed._valid_bttv_id("ZZZZZZZZZZZZ") is None
        assert emote_seed._valid_bttv_id("60ca186e/f8b3") is None
        assert emote_seed._valid_bttv_id(None) is None


class TestEnsureSeededValidatesIds:
    def test_invalid_provider_ids_seeded_name_only(self):
        fake_map = {
            "KEKW": "60ca186ef8b3f62601c3eb1d",  # valid
            "Evil": "../../etc/passwd",  # invalid -> None
            "Short": "abc",  # invalid -> None
        }
        with (
            patch.object(emote_seed, "select_dictionary_count_db", return_value=0),
            patch.object(emote_seed, "_load_bttv_map", return_value=fake_map),
            patch.object(emote_seed, "seed_emote_dictionary_db") as mock_seed,
        ):
            emote_seed.ensure_emote_dictionary_seeded()

        mock_seed.assert_called_once()
        rows = {name: provider_id for name, _source, provider_id in mock_seed.call_args[0][0]}
        assert rows["KEKW"] == "60ca186ef8b3f62601c3eb1d"
        assert rows["Evil"] is None
        assert rows["Short"] is None

    def test_skips_when_already_seeded(self):
        with (
            patch.object(emote_seed, "select_dictionary_count_db", return_value=5),
            patch.object(emote_seed, "seed_emote_dictionary_db") as mock_seed,
        ):
            emote_seed.ensure_emote_dictionary_seeded()
        mock_seed.assert_not_called()
