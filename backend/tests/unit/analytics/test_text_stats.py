"""Unit tests for the pure Czech-aware text statistics (no DB)."""

from unittest.mock import patch

from stream_sniper.analytics import text_stats


class TestTokenize:
    def test_lowercases_and_strips_punctuation(self):
        assert text_stats.tokenize("Hello, WORLD! @user :)") == ["hello", "world", "user"]

    def test_keeps_czech_accented_letters(self):
        assert text_stats.tokenize("Ahoj světe, jak?") == ["ahoj", "světe", "jak"]

    def test_empty_and_none(self):
        assert text_stats.tokenize("") == []
        assert text_stats.tokenize(None) == []


class TestTopPhrases:
    def test_stopwords_dropped_as_unigrams_and_in_bigrams(self):
        # "je" and "to" are stopwords: only "super" survives; no bigram spans a stopword.
        rows = [("je to super", 1, 3), ("je to super", 2, 3), ("je to super", 3, 3)]
        phrases = dict((p, (u, c)) for p, u, c in text_stats.top_phrases(rows, set(), min_count=3))
        assert "super" in phrases
        assert "je" not in phrases and "to" not in phrases
        assert "je to" not in phrases and "to super" not in phrases

    def test_bigrams_counted(self):
        rows = [("poggers clip", 1, 3), ("poggers clip", 2, 2)]
        phrases = dict((p, u) for p, u, _c in text_stats.top_phrases(rows, set(), min_count=3))
        assert phrases["poggers clip"] == 5  # 3 + 2 occurrences

    def test_min_count_filters_rare_phrases(self):
        rows = [("rareword here", 1, 1)]  # each phrase occurs once, below min_count=3
        assert text_stats.top_phrases(rows, set(), min_count=3) == []

    def test_emote_names_excluded(self):
        rows = [("kappa poggers", 1, 3), ("kappa poggers", 2, 3)]
        phrases = dict((p, u) for p, u, _c in text_stats.top_phrases(rows, {"kappa"}, min_count=3))
        assert "kappa" not in phrases  # emote unigram filtered
        assert "kappa poggers" not in phrases  # bigram touching an emote filtered
        assert phrases["poggers"] == 6

    def test_chatter_count_dedupes_one_chatter_across_multiple_texts(self):
        # chatter 10 uses "poggers" across two DIFFERENT texts (3 + 2 sends); chatter 20 uses it once.
        # usage_count sums all occurrences (6), but chatter_count must be 2, never summed per text.
        rows = [
            ("poggers moment", 10, 3),
            ("poggers clip", 10, 2),
            ("poggers", 20, 1),
        ]
        result = {p: (usage, chatters) for p, usage, chatters in text_stats.top_phrases(rows, set(), min_count=3)}
        assert result["poggers"] == (6, 2)


class TestPhraseStatsBounds:
    def test_chatter_set_saturates_at_cap(self):
        # One phrase used by more distinct chatters than the cap: usage keeps counting every
        # occurrence, but the distinct-chatter set (and thus chatter_count) saturates at the cap.
        n = text_stats._MAX_CHATTERS_PER_PHRASE + 76
        rows = [("poggers", cid, 1) for cid in range(n)]
        usage, chatters = text_stats.phrase_stats(rows, set())
        assert usage["poggers"] == n
        assert len(chatters["poggers"]) == text_stats._MAX_CHATTERS_PER_PHRASE

    def test_singleton_phrases_pruned_past_threshold(self):
        # Recurring phrase survives; the long tail of one-off singletons is pruned once the usage
        # map grows past the (patched-small) threshold, keeping memory bounded.
        with patch.object(text_stats, "_PHRASE_PRUNE_THRESHOLD", 4):
            rows = [("keep", 1, 1), ("keep", 2, 1)]
            rows += [(f"junk{i}", 100 + i, 1) for i in range(40)]
            usage, chatters = text_stats.phrase_stats(rows, set())
        assert usage["keep"] == 2  # recurring phrase preserved with full count
        assert len(chatters["keep"]) == 2
        # Pruning demonstrably shrank the map far below the 42 distinct phrases inserted.
        assert len(usage) < 42
        assert "keep" in usage


class TestDistinctivePhrases:
    def test_over_represented_window_phrase_ranks_first_by_lift(self):
        window_rows = [("insane play", 1), ("insane play", 1), ("insane", 1)]
        # per-minute stream frequencies: "insane play" is rare in the stream -> high lift.
        stream_freq = {"insane": 1.0, "play": 2.0, "insane play": 0.1}
        result = text_stats.distinctive_phrases(window_rows, stream_freq, set(), limit=5)
        phrases = [p for p, _c, _lift in result]
        assert phrases[0] == "insane play"
        lifts = {p: lift for p, _c, lift in result}
        assert lifts["insane play"] == 20.0  # window count 2 / 0.1

    def test_unknown_phrase_uses_epsilon_floor_not_zero_division(self):
        result = text_stats.distinctive_phrases([("brandnew thing", 1)], {}, set(), limit=5)
        assert result  # does not raise; finite lift
        assert all(lift > 0 for _p, _c, lift in result)
