"""Application query assembling the single-emote drill-down from the emote rollups."""

from stream_sniper.database.gateways.analytics.emote_detail_gateway import (
    select_emote_meta_db,
    select_emote_recent_streams_db,
    select_emote_top_creators_db,
    select_emote_totals_db,
    select_emote_weekly_usage_db,
)

from .emote_detail_models import (
    EmoteCreatorUsage,
    EmoteDetail,
    EmoteMeta,
    EmoteStreamUsage,
    EmoteTotals,
    EmoteWeeklyUsage,
)

_TOP_CREATORS_LIMIT = 10
_RECENT_STREAMS_LIMIT = 10
_TREND_WEEKS = 12


def get_emote_detail(emote_id: int) -> EmoteDetail | None:
    """Assemble the drill-down, or None when the emote id is not in the dictionary.

    A dictionary emote with no recorded usage is a legitimate result (zero totals,
    empty sections) — only an unknown id returns None so the HTTP layer can 404.
    """
    meta = select_emote_meta_db(emote_id)
    if meta is None:
        return None

    return EmoteDetail(
        meta=EmoteMeta.from_row(meta),
        totals=EmoteTotals.from_row(select_emote_totals_db(emote_id)),
        top_creators=[
            EmoteCreatorUsage.from_row(row) for row in select_emote_top_creators_db(emote_id, _TOP_CREATORS_LIMIT)
        ],
        weekly_usage=[EmoteWeeklyUsage.from_row(row) for row in select_emote_weekly_usage_db(emote_id, _TREND_WEEKS)],
        recent_streams=[
            EmoteStreamUsage.from_row(row) for row in select_emote_recent_streams_db(emote_id, _RECENT_STREAMS_LIMIT)
        ],
    )
