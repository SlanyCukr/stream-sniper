"""
Runtime patch for chat_downloader's Twitch VOD chat download.

chat_downloader 0.2.8 (unmaintained) fetches Twitch data via Automatic
Persisted Queries, sending only a hardcoded ``sha256Hash`` per GraphQL
operation. Twitch has since de-registered the ``VideoMetadata`` hash, so the
first request of every VOD download now fails with ``PersistedQueryNotFound``
(surfacing downstream as ``KeyError: 'data'``) and no chat is ever collected.

Every other operation the VOD path uses (``VideoCommentsByOffsetOrCursor``,
``ChatList_Badges``) still resolves, so we patch only ``VideoMetadata`` to send
the full GraphQL query text instead of a persisted-query hash. Sending the query
body is hash-independent and won't break again when Twitch rotates hashes.

Importing this module applies the patch once (idempotent).
"""

from chat_downloader.sites.twitch import TwitchChatDownloader

# chat_downloader only reads title, lengthSeconds and owner.login from the
# VideoMetadata response (see TwitchChatDownloader.get_chat_by_vod_id).
_VIDEO_METADATA_QUERY = (
    "query VideoMetadata($videoID: ID!) { "
    "video(id: $videoID) { title lengthSeconds owner { id login displayName } } }"
)

_PATCH_FLAG = "_stream_sniper_gql_patched"


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
    return self._download_base_gql(ops)


def apply_patch():
    """Idempotently replace TwitchChatDownloader._download_gql with the patched version."""
    if getattr(TwitchChatDownloader, _PATCH_FLAG, False):
        return
    TwitchChatDownloader._download_gql = _patched_download_gql
    setattr(TwitchChatDownloader, _PATCH_FLAG, True)


apply_patch()
