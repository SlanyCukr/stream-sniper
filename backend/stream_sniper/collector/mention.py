"""Canonical @mention -> chatter-nick token, shared by the archived and live collectors.

Both ingestion paths tag a message with the chatter it @mentions, and both must
derive the same token from the same text -- otherwise the archived (VOD) and live
(IRC) paths would resolve the same message to different ``tagged_chatter_id``s. The
token is the lowercased word right after the first ``@``, with trailing sentence
punctuation stripped so ``@creator.`` and ``@creator`` tag the same chatter. The
extractor lives here so the two paths cannot drift.
"""

# Trailing sentence punctuation that is never part of a Twitch nick, so
# "@creator." mentions the same chatter as "@creator".
_MENTION_TRAILING_PUNCT = ".,:;!?"


def mention_token(message: str) -> str | None:
    """Lowercased @mention token, or ``None`` when the message mentions no one.

    The token is the word following the first ``@`` (up to the next space), with
    trailing sentence punctuation stripped. Returns ``None`` when there is no ``@``
    or nothing remains after stripping.
    """
    if "@" not in message:
        return None
    token = message.lower().split("@", 1)[1].split(" ", 1)[0].rstrip(_MENTION_TRAILING_PUNCT)
    return token or None
