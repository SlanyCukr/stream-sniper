"""BTTV emote dictionary seeding.

The packaged ``data/bttv_emotes.json`` (a ``{name: bttv_id}`` map) is bulk-loaded into
``emote_dictionary`` with ``source='bttv'`` exactly once. Called lazily by the rollup engine
before the per-stream emote rollup so the dictionary exists on a fresh database.
"""

import json
from functools import lru_cache
from importlib import resources
from typing import Dict, List, Optional, Tuple

from ..database.emote_dictionary_table_gateway import (
    seed_emote_dictionary_db,
    select_dictionary_count_db,
)
from ..logging_config import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_bttv_map() -> Dict[str, str]:
    with resources.files("stream_sniper.analytics.data").joinpath("bttv_emotes.json").open(
        "r", encoding="utf-8"
    ) as fh:
        return json.load(fh)


def ensure_emote_dictionary_seeded() -> None:
    """Seed the BTTV rows if not already present. Idempotent and cheap on the hot path.

    Skips the bulk insert once any ``source='bttv'`` row exists (the count probe is a single
    indexed lookup). ``seed_emote_dictionary_db`` uses ON CONFLICT DO NOTHING, so a concurrent
    or partial prior seed still converges.
    """
    if select_dictionary_count_db("bttv") > 0:
        return

    rows: List[Tuple[str, str, Optional[str]]] = [
        (name, "bttv", provider_id) for name, provider_id in _load_bttv_map().items()
    ]
    if not rows:
        return
    seed_emote_dictionary_db(rows)
    logger.info(f"Seeded emote_dictionary with {len(rows)} BTTV emotes")
