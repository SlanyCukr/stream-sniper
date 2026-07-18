"""Rule-based chatter archetype badges derived from passport data.

A pure, deterministic function that turns the already-assembled passport aggregates
(loyalty/home share + lifetime totals + first-seen time) into a small set of honest
identity badges. It performs NO database access and derives NOTHING that would need a
full message scan (there is no per-chatter emote/subscriber/hour-of-day rollup, so no
emote/sub/night-owl badges are invented).

Thresholds (each documented inline):

* ``loyalist``    — home_share >= 0.70 AND streams_attended >= 3
* ``wanderer``    — creators_visited >= 5 AND home_share < 0.40
* ``marathoner``  — total_messages / streams_attended >= 100 AND streams_attended >= 3
* ``chatterbox``  — total_messages >= 5000
* ``veteran``     — first_seen at least 180 days before ``now``
* ``newcomer``    — first_seen within the last 30 days (inclusive)

Only applicable badges are emitted, in the stable order above, capped at 4.
``loyalist``/``wanderer`` are mutually exclusive by their share bounds, as are
``veteran``/``newcomer`` by their age bounds.
"""

from datetime import datetime, timedelta

from stream_sniper.database.core.wire_format import WIRE_TS_FORMAT

from .passport_models import PassportArchetype

_MAX_ARCHETYPES = 4

_LOYALIST_MIN_SHARE = 0.70
_LOYALIST_MIN_STREAMS = 3
_WANDERER_MIN_CREATORS = 5
_WANDERER_MAX_SHARE = 0.40
_MARATHONER_MIN_AVG = 100
_MARATHONER_MIN_STREAMS = 3
_CHATTERBOX_MIN_MESSAGES = 5000
_VETERAN_MIN_AGE = timedelta(days=180)
_NEWCOMER_MAX_AGE = timedelta(days=30)


def _parse_first_seen(first_seen: str | None, now: datetime) -> timedelta | None:
    """Age of ``first_seen`` relative to ``now``, or None when unknown/unparseable.

    Wire timestamps are naive second-precision UTC strings; ``now`` is expected to be
    tz-aware (``datetime.now(UTC)``). The parsed value is stamped with ``now``'s tzinfo
    so the subtraction is well-defined regardless of whether the caller passed an
    aware or naive ``now``.
    """
    if first_seen is None:
        return None
    try:
        parsed = datetime.strptime(first_seen, WIRE_TS_FORMAT).replace(tzinfo=now.tzinfo)
    except ValueError:
        return None
    return now - parsed


def compute_archetypes(
    *,
    total_messages: int,
    streams_attended: int,
    creators_visited: int,
    home_share: float | None,
    first_seen: str | None,
    now: datetime,
) -> list[PassportArchetype]:
    """Deterministic archetype badges for one chatter, in stable order, capped at 4.

    :param total_messages: lifetime messages across every creator (``totals.messages``).
    :param streams_attended: lifetime streams attended (``totals.streams_attended``).
    :param creators_visited: distinct creators chatted in (``totals.creators_visited``).
    :param home_share: the home channel's message share (``home_channel.share``), or
        None when the chatter has no recorded messages.
    :param first_seen: the lifetime first-message wire timestamp (``totals.first_seen``).
    :param now: reference time for age thresholds (caller passes ``datetime.now(UTC)``).
    """
    badges: list[PassportArchetype] = []

    # Loyalist: overwhelmingly devoted to a single home channel, with real tenure.
    if (
        home_share is not None
        and home_share >= _LOYALIST_MIN_SHARE
        and streams_attended >= _LOYALIST_MIN_STREAMS
    ):
        badges.append(
            PassportArchetype(
                key="loyalist",
                label="Loyalist",
                description="Sends 70%+ of their messages to one channel across 3 or more streams.",
            )
        )

    # Wanderer: spread thin across many channels with no single home.
    if (
        home_share is not None
        and creators_visited >= _WANDERER_MIN_CREATORS
        and home_share < _WANDERER_MAX_SHARE
    ):
        badges.append(
            PassportArchetype(
                key="wanderer",
                label="Wanderer",
                description="Active in 5+ channels with no single home (top channel under 40%).",
            )
        )

    # Marathoner: high message output per stream, sustained over several streams.
    if streams_attended >= _MARATHONER_MIN_STREAMS and total_messages / streams_attended >= _MARATHONER_MIN_AVG:
        badges.append(
            PassportArchetype(
                key="marathoner",
                label="Marathoner",
                description="Averages 100+ messages per stream over 3 or more streams.",
            )
        )

    # Chatterbox: sheer lifetime volume.
    if total_messages >= _CHATTERBOX_MIN_MESSAGES:
        badges.append(
            PassportArchetype(
                key="chatterbox",
                label="Chatterbox",
                description="Has sent over 5,000 messages across the scene.",
            )
        )

    age = _parse_first_seen(first_seen, now)
    if age is not None:
        # Veteran: first seen long ago.
        if age >= _VETERAN_MIN_AGE:
            badges.append(
                PassportArchetype(
                    key="veteran",
                    label="Veteran",
                    description="First seen more than 180 days ago.",
                )
            )
        # Newcomer: first appeared recently.
        elif age <= _NEWCOMER_MAX_AGE:
            badges.append(
                PassportArchetype(
                    key="newcomer",
                    label="Newcomer",
                    description="First appeared within the last 30 days.",
                )
            )

    return badges[:_MAX_ARCHETYPES]
