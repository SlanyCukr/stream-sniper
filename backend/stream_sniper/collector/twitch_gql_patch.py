"""
Runtime patches for chat_downloader's Twitch VOD chat download.

Patch 1 — de-registered persisted query:
chat_downloader 0.2.8 (unmaintained) fetches Twitch data via Automatic
Persisted Queries, sending only a hardcoded ``sha256Hash`` per GraphQL
operation. Twitch has since de-registered the ``VideoMetadata`` hash, so the
first request of every VOD download now fails with ``PersistedQueryNotFound``
(surfacing downstream as ``KeyError: 'data'``) and no chat is ever collected.

Every other operation the VOD path uses (``VideoCommentsByOffsetOrCursor``,
``ChatList_Badges``) still resolves, so we patch only ``VideoMetadata`` to send
the full GraphQL query text instead of a persisted-query hash. Sending the query
body is hash-independent and won't break again when Twitch rotates hashes.

Patch 2 — silent mid-VOD truncation:
``_get_chat_messages_by_vod_id`` paginates comments and does
``if not comments: break`` — so a single transient GQL response with
``data.video.comments = null`` (rate-limit shaping, server hiccup) silently
ends the download mid-VOD. Observed in production as wildly different message
counts for the same VOD across runs (117,115 vs 41,566). We retry
``VideoCommentsByOffsetOrCursor`` responses whose ``comments`` is falsy with
backoff before letting the library see them; genuinely chat-less VODs still
terminate (after the short retry budget).

Importing this module applies the patches once (idempotent).
"""

import time

from chat_downloader.sites.twitch import TwitchChatDownloader

from ..logging_config import get_logger

_logger = get_logger(__name__)

# chat_downloader only reads title, lengthSeconds and owner.login from the
# VideoMetadata response (see TwitchChatDownloader.get_chat_by_vod_id).
_VIDEO_METADATA_QUERY = (
    "query VideoMetadata($videoID: ID!) { "
    "video(id: $videoID) { title lengthSeconds owner { id login displayName } } }"
)

_PATCH_FLAG = "_stream_sniper_gql_patched"

# Retry budget for comment pages that come back without a comments object.
_NULL_COMMENTS_RETRIES = 4
_NULL_COMMENTS_BACKOFF_BASE = 1.5  # seconds; grows 1.5, 3, 6, 12


def _comments_missing(response, ops):
    """True if a VideoCommentsByOffsetOrCursor response lacks the comments object."""
    if not any(op.get("operationName") == "VideoCommentsByOffsetOrCursor" for op in ops):
        return False
    try:
        video = response[0]["data"]["video"]
    except (KeyError, IndexError, TypeError):
        return True
    return not video or not video.get("comments")


def _patched_download_gql(self, ops):
    for op in ops:
        if op.get("operationName") == "VideoMetadata":
            # Full query instead of the de-registered persisted-query hash.
            op["variables"] = {"videoID": op["variables"].get("videoID")}
            op["query"] = _VIDEO_METADATA_QUERY
            op.pop("extensions", None)
        else:
            op["extensions"] = {
                "persistedQuery": {
                    "version": 1,
                    "sha256Hash": self._OPERATION_HASHES[op["operationName"]],
                }
            }

    response = self._download_base_gql(ops)

    # Patch 2: a falsy comments object ends the library's pagination loop, so
    # a transient degraded response truncates the whole download. Retry before
    # handing it back; if it is still empty after the budget, the VOD really
    # has no (more) chat and the normal termination path applies.
    retry = 0
    while _comments_missing(response, ops) and retry < _NULL_COMMENTS_RETRIES:
        delay = _NULL_COMMENTS_BACKOFF_BASE * (2**retry)
        retry += 1
        _logger.warning(
            f"VideoCommentsByOffsetOrCursor returned no comments object "
            f"(attempt {retry}/{_NULL_COMMENTS_RETRIES}); retrying in {delay:.1f}s "
            f"to avoid silent mid-VOD truncation"
        )
        time.sleep(delay)
        response = self._download_base_gql(ops)

    return response


def apply_patch():
    """Idempotently replace TwitchChatDownloader._download_gql with the patched version."""
    if getattr(TwitchChatDownloader, _PATCH_FLAG, False):
        return
    TwitchChatDownloader._download_gql = _patched_download_gql
    setattr(TwitchChatDownloader, _PATCH_FLAG, True)


apply_patch()
