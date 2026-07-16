"""Application boundary for streaming a stream's chat rows."""

from collections.abc import Iterator
from typing import Any

from ...database.core.connection_pool import DatabaseConnectionPool
from ...database.gateways.chat.message_export_gateway import iter_stream_message_export_db
from ...database.gateways.streams.stream_table_gateway import select_stream_comprehensive_db


def stream_exists(stream_id: int) -> bool:
    return select_stream_comprehensive_db(stream_id) is not None


def iter_stream_export_rows(
    stream_id: int,
    pool: DatabaseConnectionPool | None,
) -> Iterator[dict[str, Any]]:
    for row in iter_stream_message_export_db(stream_id, pool):
        yield row._asdict()
