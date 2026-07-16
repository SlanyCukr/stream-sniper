"""Tracked-streamer creation workflow and domain failures."""

import asyncio
from dataclasses import dataclass
from typing import Protocol

from stream_sniper.application.tracking.models import TrackedStreamer

from ...database.gateways.identity.creator_table_gateway import find_or_insert_creator_id_db, select_creator_id_db
from ...database.gateways.tracking.tracked_streamers_table_gateway import (
    insert_tracked_streamer_db,
    select_tracked_streamer_by_id_db,
    streamer_exists_db,
)


@dataclass(frozen=True)
class CreatorProfile:
    """Profile fields required by the tracked-streamer workflow."""

    twitch_user_id: str
    display_name: str
    profile_image_url: str


class CreatorProfileLookup(Protocol):
    """Creator lookup port supplied by the API composition root."""

    async def ensure_initialized(self) -> None: ...

    async def get_creator_profile(self, login: str) -> CreatorProfile | None: ...


class StreamerAlreadyTrackedError(ValueError):
    """Raised when tracking already exists for the requested login."""


class StreamerNotFoundError(ValueError):
    """Raised when Twitch has no profile for the requested login."""


class TwitchProfileLookupError(RuntimeError):
    """Raised when Twitch profile resolution fails operationally."""


class TrackedStreamerCreationError(RuntimeError):
    """Raised when persistence cannot complete and reload the workflow."""


async def create_tracked_streamer(
    *,
    twitch_api: CreatorProfileLookup,
    twitch_username: str,
    created_by: int,
    notes: str | None,
    is_active: bool,
    processing_enabled: bool,
) -> TrackedStreamer:
    """Resolve the creator, persist tracking, and return the reloaded record."""
    if await asyncio.to_thread(streamer_exists_db, twitch_username):
        raise StreamerAlreadyTrackedError

    creator_id = await asyncio.to_thread(select_creator_id_db, twitch_username)
    display_name = twitch_username
    if creator_id is None:
        await twitch_api.ensure_initialized()
        profile = await twitch_api.get_creator_profile(twitch_username)
        if profile is None:
            raise StreamerNotFoundError
        creator_id = await asyncio.to_thread(
            find_or_insert_creator_id_db,
            twitch_username,
            profile.display_name,
            profile.profile_image_url,
            profile.twitch_user_id,
        )
        if creator_id is None:
            raise TrackedStreamerCreationError("Creator insert returned no identifier")
        display_name = profile.display_name

    tracked_streamer_id = await asyncio.to_thread(
        insert_tracked_streamer_db,
        creator_id=creator_id,
        twitch_username=twitch_username,
        display_name=display_name,
        created_by=created_by,
        notes=notes,
        is_active=is_active,
        processing_enabled=processing_enabled,
    )
    if tracked_streamer_id is None:
        raise TrackedStreamerCreationError("Tracked streamer insert returned no identifier")

    streamer = await asyncio.to_thread(select_tracked_streamer_by_id_db, tracked_streamer_id)
    if streamer is None:
        raise TrackedStreamerCreationError("Created tracked streamer could not be reloaded")
    return streamer
