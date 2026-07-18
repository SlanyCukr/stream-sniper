"""Community and audience persistence projections."""

from typing import NamedTuple


class AudienceSummaryRow(NamedTuple):
    current: int
    previous: int
    retained: int
    gained: int
    lapsed: int


class AudienceAssociationRow(NamedTuple):
    creator_id: int
    nick: str
    display_name: str
    chatter_count: int


class AudienceMovementRows(NamedTuple):
    summary: AudienceSummaryRow
    prior_channels_for_gained: tuple[AudienceAssociationRow, ...]
    current_channels_for_lapsed: tuple[AudienceAssociationRow, ...]


class CommunityCreatorRow(NamedTuple):
    creator_id: int
    nick: str
    display_name: str
    chatters: int
    regulars: int
    computed_at: str


class CommunityPairRow(NamedTuple):
    creator_a: int
    creator_b: int
    shared_chatters: int
    shared_regulars: int


class CreatorNeighborRow(NamedTuple):
    creator_id: int
    nick: str
    display_name: str
    shared_chatters: int
    shared_regulars: int


class ChatCompanionRow(NamedTuple):
    chatter_id: int
    nick: str
    shared_streams: int
