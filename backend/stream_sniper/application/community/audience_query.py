"""Creator audience movement assembly."""

from stream_sniper.database.gateways.community.audience_movement_table_gateway import (
    select_creator_audience_movement_db,
)
from stream_sniper.database.gateways.community.records import AudienceAssociationRow

from .audience_models import AudienceAssociation, AudienceMovement


def _association(row: AudienceAssociationRow) -> AudienceAssociation:
    return AudienceAssociation(
        creator_id=row.creator_id,
        nick=row.nick,
        display_name=row.display_name,
        chatter_count=row.chatter_count,
    )


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
        prior_channels_for_gained=[_association(row) for row in movement.prior_channels_for_gained],
        current_channels_for_lapsed=[_association(row) for row in movement.current_channels_for_lapsed],
    )
