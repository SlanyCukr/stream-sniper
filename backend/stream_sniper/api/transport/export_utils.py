"""Shared CSV/NDJSON serialization helpers for export endpoints.

Pure serializers (stdlib csv/json only) so they unit-test hermetically; the
``csv_response`` wrapper is the one FastAPI-aware convenience for the small
in-memory aggregate exports.
"""

import csv
import io
import json
from collections.abc import Iterable, Iterator
from typing import Any

from fastapi import Response


def csv_content(fieldnames: list[str], rows: list[dict[str, Any]]) -> str:
    """Render dict rows as one in-memory CSV document (header + quoted rows)."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)
    return buffer.getvalue()


def csv_response(
    fieldnames: list[str],
    rows: list[dict[str, Any]],
    filename: str,
    extra_headers: dict[str, str] | None = None,
) -> Response:
    """Build an attachment CSV Response from dict rows (small payloads only)."""
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    if extra_headers:
        headers.update(extra_headers)
    return Response(content=csv_content(fieldnames, rows), media_type="text/csv", headers=headers)


def iter_ndjson(rows: Iterable[dict[str, Any]]) -> Iterator[str]:
    """Lazily serialize dict rows as NDJSON lines (one JSON object per line)."""
    for row in rows:
        yield json.dumps(row, ensure_ascii=False) + "\n"


def iter_csv(fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> Iterator[str]:
    """Lazily serialize dict rows as CSV: a header line first, then one quoted row per chunk."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    yield buffer.getvalue()
    for row in rows:
        buffer.seek(0)
        buffer.truncate()
        writer.writerow(row)
        yield buffer.getvalue()
