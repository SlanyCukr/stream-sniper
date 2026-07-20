"""Single owner for the API wire timestamp format.

Timestamps cross the wire as ``"%Y-%m-%dT%H:%M:%S"`` (an ISO-8601 second-precision
string). That shape has two representations that MUST stay in sync:

* the Python ``strptime``/``strftime`` directive (:data:`WIRE_TS_FORMAT`), used by
  application/analytics code that parses or renders those strings, and
* the PostgreSQL ``TO_CHAR`` mask (:data:`WIRE_TS_SQL_MASK`), used by gateways that
  format ``timestamp`` columns into the same string in SQL.

This module is the only place both live. Change one representation here and change
the other in lockstep -- callers import from here instead of re-declaring a local
copy, so a drift can never hide in a distant module.
"""

WIRE_TS_FORMAT = "%Y-%m-%dT%H:%M:%S"
"""Python ``strptime``/``strftime`` directive for the wire timestamp."""

WIRE_TS_SQL_MASK = 'YYYY-MM-DD"T"HH24:MI:SS'
"""PostgreSQL ``TO_CHAR`` mask matching :data:`WIRE_TS_FORMAT`."""

WIRE_TS_US_SQL_MASK = f"{WIRE_TS_SQL_MASK}.US"
"""Microsecond-precision variant of the mask, used where message ordering must
survive the round trip (chat replay/search/export keyset pagination)."""


def to_char_wire(expr: str) -> str:
    """Build a ``TO_CHAR(<expr>, '<wire mask>')`` SQL fragment for gateway queries.

    ``expr`` is always a trusted column or expression literal written inline in
    gateway code (e.g. ``"s.start"`` or ``"svs.sampled_at AT TIME ZONE 'UTC'"``);
    it is NEVER user input, so interpolating it into the returned SQL is safe.
    """
    return f"TO_CHAR({expr}, '{WIRE_TS_SQL_MASK}')"


def to_char_wire_us(expr: str) -> str:
    """Microsecond-precision sibling of :func:`to_char_wire` (same trust contract)."""
    return f"TO_CHAR({expr}, '{WIRE_TS_US_SQL_MASK}')"
