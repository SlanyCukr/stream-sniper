"""Application boundary for the chat-export endpoint's gateway access.

These two helpers are deliberately thin, but they are NOT dead pass-throughs: the
package-contract test ``test_cross_gateway_http_handlers_delegate_to_application``
forbids ``database.gateways`` imports in ``stream_report_endpoints.py`` (which owns the
export route). This module is where that endpoint's gateway calls legitimately live --
existence check and the ``_asdict()`` projection of raw export rows -- so the handler
stays inside the layering contract without a gateway import.
"""

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
