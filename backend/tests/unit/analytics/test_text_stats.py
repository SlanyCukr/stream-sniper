"""Unit tests for the pure Czech-aware text statistics (no DB)."""

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
