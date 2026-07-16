"""Creator lookup and Twitch-backed creation boundary for collectors."""

from typing import cast

from ...database.gateways.identity.creator_table_gateway import find_or_insert_creator_id_db, select_creator_id_db
from ..twitch_api import SyncTwitchClient


class CreatorCreationError(RuntimeError):
    """Raised when a Twitch creator cannot be resolved into a database row."""


class CreatorResolver:
    def resolve(self, twitch_username: str, twitch_client: SyncTwitchClient) -> int:
        creator_id = select_creator_id_db(twitch_username)
        if creator_id:
            return cast(int, creator_id)

        profile = twitch_client.get_creator_profile(twitch_username)
        if profile is None:
            raise CreatorCreationError(f"Creator {twitch_username} does not exist on Twitch")
        creator_id = find_or_insert_creator_id_db(
            twitch_username,
            profile.display_name,
            profile.profile_image_url,
            profile.twitch_user_id,
        )
        if not creator_id:
            raise CreatorCreationError(f"Failed to create creator {twitch_username}")
        return cast(int, creator_id)
