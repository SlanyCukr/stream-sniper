"""Patch-field sentinels shared by database gateways."""


class Unset:
    """Typed sentinel for explicit patch fields that were not supplied."""

    __slots__ = ()


UNSET = Unset()
