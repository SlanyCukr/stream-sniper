"""BTTV emote dictionary seeding.

The packaged ``data/bttv_emotes.json`` (a ``{name: bttv_id}`` map) is bulk-loaded into
``emote_dictionary`` with ``source='bttv'`` exactly once. Called lazily by the rollup engine
before the per-stream emote rollup so the dictionary exists on a fresh database.
"""

import json
import re
from functools import lru_cache
from importlib import resources

from ...database.gateways.chat.emote_dictionary_table_gateway import (
    seed_emote_dictionary_db,
    select_dictionary_count_db,
)
from ...logging_config import get_logger

logger = get_logger(__name__)

# A BTTV emote id is a 24-hex-char Mongo ObjectId; accept a tolerant hex range. provider_id doubles
# as a CDN URL path segment, so anything that fails validation is seeded name-only (provider_id None).
_BTTV_ID_RE = re.compile(r"^[a-f0-9]{12,32}$")


def _valid_bttv_id(provider_id: str | None) -> str | None:
    if provider_id is not None and _BTTV_ID_RE.match(provider_id):
        return provider_id
    return None


@lru_cache(maxsize=1)
def _load_bttv_map() -> dict[str, str]:
    with resources.files("stream_sniper.analytics.data").joinpath("bttv_emotes.json").open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict) or not all(
        isinstance(key, str) and isinstance(value, str) for key, value in payload.items()
    ):
        raise ValueError("Packaged BTTV emote map must contain only string keys and values")
    return dict(payload)


def ensure_emote_dictionary_seeded() -> None:
    """Seed the BTTV rows if not already present. Idempotent and cheap on the hot path.

    Skips the bulk insert once any ``source='bttv'`` row exists (the count probe is a single
    indexed lookup). ``seed_emote_dictionary_db`` uses ON CONFLICT DO NOTHING, so a concurrent
    or partial prior seed still converges.
    """
    if select_dictionary_count_db("bttv") > 0:
        return

    rows: list[tuple[str, str, str | None]] = [
        (name, "bttv", _valid_bttv_id(provider_id)) for name, provider_id in _load_bttv_map().items()
    ]
    if not rows:
        return
    seed_emote_dictionary_db(rows)
    logger.info(f"Seeded emote_dictionary with {len(rows)} BTTV emotes")
