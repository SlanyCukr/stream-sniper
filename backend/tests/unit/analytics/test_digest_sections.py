"""Unit tests for the multi-section scene-intelligence digest.

Section formatters are pure and tested directly; ``build_digest`` is tested with
all five gateways monkeypatched to assert composition order and empty-section
elision. The gateway SQL itself is covered elsewhere (unit + scratch-Postgres).
"""

from unittest.mock import patch

from stream_sniper.analytics.operations.digest import (
    build_digest,
    format_highlights,
    format_top_chatters,
    format_trending_copypastas,
    format_trending_emotes,
)
from stream_sniper.database.gateways.analytics.scene_trends_gateway import (
    TrendingCopypastaRow,
    TrendingEmoteRow,
)
from stream_sniper.database.gateways.content.records import SceneEventRow
from stream_sniper.database.gateways.content.scene_highlights_gateway import SceneHighlightRow
from stream_sniper.database.gateways.creators.scene_chatter_rankings_gateway import (
    SceneChatterRankRow,
)


def _copypasta(current=340, prior=120):
    return TrendingCopypastaRow(
        message_text_id=1,
        text="OMEGALUL nice one chat",
        current_usage=current,
        prior_usage=prior,
        stream_count=8,
        creator_count=5,
        first_seen="2026-07-10T09:00:00",
    )


def _emote(current=900, prior=950):
    return TrendingEmoteRow(
        emote_id=42,
        name="PogU",
        source="bttv",
        provider_id="x1",
        current_usage=current,
        prior_usage=prior,
        chatter_reach=210,
        creator_count=4,
        first_seen="2026-05-01T00:00:00",
    )


def _chatter(nick="alice", messages=4200):
    return SceneChatterRankRow(
        chatter_id=1,
        nick=nick,
        total_messages=messages,
        streams_attended=20,
        creators_visited=8,
        first_seen=None,
        home_creator_id=3,
        home_creator_nick="alpha",
        home_creator_display_name="Alpha",
        home_messages=2000,
        lifetime_messages=9000,
        lifetime_streams=40,
        lifetime_creators=10,
        lifetime_home_messages=5000,
    )


def _highlight(ratio: float | None = 4.5, phrases=None):
    return SceneHighlightRow(
        stream_id=77,
        stream_title="big stream",
        twitch_id=123,
        creator_id=3,
        creator_nick="alpha",
        creator_display_name="Alpha",
        bucket_minute="2026-07-15T20:31:00",
        offset_seconds=5460,
        ratio=ratio,
        message_count=320,
        unique_chatters=140,
        sub_share=None,
        emote_share=None,
        top_phrases=phrases,
        sample_messages=None,
        clip_url=None,
        review_status=None,
    )


class TestSectionFormatters:
    def test_copypastas_render_velocity_and_spread(self):
        section = format_trending_copypastas([_copypasta()])
        assert section is not None
        assert section.startswith("### Rising copypastas")
        assert '"OMEGALUL nice one chat" — 340 uses (▲ +183%), 5 channels' in section

    def test_emotes_render_falling_and_new_deltas(self):
        section = format_trending_emotes([_emote(900, 950), _emote(30, 0)])
        assert section is not None
        assert "**PogU** (bttv) — 900 uses (▼ -5%), 4 channels" in section
        assert "30 uses (new), 4 channels" in section

    def test_chatters_render_rank_and_home_channel(self):
        section = format_top_chatters([_chatter()])
        assert section is not None
        assert "1. **alice** — 4200 msgs across 8 channels, home: Alpha" in section

    def test_highlights_render_phrase_ratio_and_deep_link(self):
        section = format_highlights([
            _highlight(phrases=[{"phrase": "CLIP IT", "count": 40, "lift": 9.0}]),
        ])
        assert section is not None
        assert '**Alpha** — "CLIP IT", 320 msgs (4.5× baseline)' in section
        assert "https://stream-sniper.slanycukr.com/stream/77" in section

    def test_highlight_without_phrases_or_ratio_degrades(self):
        section = format_highlights([_highlight(ratio=None, phrases=None)])
        assert section is not None
        assert '"chat spike", 320 msgs →' in section

    def test_empty_sections_are_none(self):
        assert format_trending_copypastas([]) is None
        assert format_trending_emotes([]) is None
        assert format_top_chatters([]) is None
        assert format_highlights([]) is None


class TestBuildDigest:
    _EVENT = SceneEventRow(
        id=1,
        event_type="record",
        occurred_at="2026-07-15T20:00:00",
        creator_id=3,
        creator_nick="alpha",
        creator_display_name="Alpha",
        stream_id=77,
        message_text_id=None,
        title="New record",
        summary="busiest stream yet",
        metadata=None,
    )

    @patch("stream_sniper.analytics.operations.digest.select_scene_highlights_db")
    @patch("stream_sniper.analytics.operations.digest.select_scene_chatter_rankings_db")
    @patch("stream_sniper.analytics.operations.digest.select_trending_emotes_db")
    @patch("stream_sniper.analytics.operations.digest.select_trending_copypastas_db")
    @patch("stream_sniper.analytics.operations.digest.select_scene_events_db")
    def test_composes_sections_in_order(self, mock_events, mock_pastas, mock_emotes, mock_ranks, mock_lights):
        mock_events.return_value = ([self._EVENT], False)
        mock_pastas.return_value = [_copypasta()]
        mock_emotes.return_value = [_emote()]
        mock_ranks.return_value = ([_chatter()], False)
        mock_lights.return_value = ([_highlight()], False)

        digest = build_digest(7, 20)

        assert digest.startswith("## Stream Sniper · 7-day scene pulse")
        order = [
            digest.index("**New record**"),
            digest.index("### Rising copypastas"),
            digest.index("### Rising emotes"),
            digest.index("### Most active chatters"),
            digest.index("### Biggest moments"),
        ]
        assert order == sorted(order)
        mock_lights.assert_called_once_with(7, None, "hype", 3, 0)

    @patch("stream_sniper.analytics.operations.digest.select_scene_highlights_db")
    @patch("stream_sniper.analytics.operations.digest.select_scene_chatter_rankings_db")
    @patch("stream_sniper.analytics.operations.digest.select_trending_emotes_db")
    @patch("stream_sniper.analytics.operations.digest.select_trending_copypastas_db")
    @patch("stream_sniper.analytics.operations.digest.select_scene_events_db")
    def test_quiet_window_elides_empty_sections(self, mock_events, mock_pastas, mock_emotes, mock_ranks, mock_lights):
        mock_events.return_value = ([], False)
        mock_pastas.return_value = []
        mock_emotes.return_value = []
        mock_ranks.return_value = ([], False)
        mock_lights.return_value = ([], False)

        digest = build_digest(7, 20)

        assert digest == (
            "## Stream Sniper · 7-day scene pulse\nNo notable captured events in this window."
        )
        assert "###" not in digest
