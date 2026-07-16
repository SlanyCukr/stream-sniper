"""Shared validation for SQL ordering fragments selected from fixed maps."""

SORT_DIRECTIONS = {"asc": "ASC", "desc": "DESC"}


def sql_direction(value: str, *, default: str = "DESC") -> str:
    return SORT_DIRECTIONS.get(value, default)
