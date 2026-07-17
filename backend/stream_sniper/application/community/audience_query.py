"""Creator audience movement assembly."""

from stream_sniper.database.gateways.community.audience_movement_table_gateway import (
    select_creator_audience_movement_db,
)

from .audience_models import AudienceAssociation, AudienceMovement


def get_audience_movement(creator_id: int, days: int, limit: int) -> AudienceMovement:
    movement = select_creator_audience_movement_db(creator_id, days, limit)
    summary = movement.summary
    return AudienceMovement(
        creator_id=creator_id,
        window_days=days,
        current_audience=summary.current,
        previous_audience=summary.previous,
        retained=summary.retained,
        gained=summary.gained,
        lapsed=summary.lapsed,
        retention_rate=round(summary.retained / summary.previous, 4) if summary.previous else None,
        gain_rate=round(summary.gained / summary.current, 4) if summary.current else None,
        prior_channels_for_gained=[AudienceAssociation.from_row(row) for row in movement.prior_channels_for_gained],
        current_channels_for_lapsed=[AudienceAssociation.from_row(row) for row in movement.current_channels_for_lapsed],
    )
