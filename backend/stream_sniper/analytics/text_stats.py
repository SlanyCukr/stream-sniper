"""Pure Czech-aware chat text statistics: tokenization, recurring phrases, distinctive phrases.

No database access. Consumed by the rollup engine (per-stream phrase rollup) and the moment
enrichment (lift-based distinctive phrases inside a spike window). Phrase counting rules that
matter for correctness:

- ``top_phrases`` input rows are ``(text, chatter_id, occurrence_count)`` — one row per distinct
  (text, chatter) pair with how many times that chatter sent that exact text. ``usage_count`` is
  total phrase occurrences (text repeats and in-text repeats both count); ``chatter_count`` is the
  number of DISTINCT chatters who used the phrase, deduped on (phrase, chatter_id) — a chatter who
  uses one phrase across several different texts is counted once, never summed per text.
"""

import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Set, Tuple

# Common Czech function words + English chat filler. These carry no signal as "recurring phrases",
# so they are dropped as unigrams and never allowed inside a kept bigram.
CZECH_STOPWORDS: Set[str] = {
    # Czech pronouns / conjunctions / prepositions / particles
    "a", "aby", "ale", "ani", "ano", "asi", "az", "až", "bez", "bude", "budem", "budeme",
    "budes", "budeš", "budou", "by", "byl", "byla", "byli", "bylo", "byly", "bych", "bychom",
    "byt", "být", "co", "což", "cz", "či", "dal", "další", "de", "do", "ho", "i", "j", "ja",
    "já", "jak", "jako", "je", "jeho", "jej", "její", "jejich", "jen", "jenž", "ještě", "ji",
    "jich", "jimi", "jinak", "jsem", "jses", "jseš", "jsi", "jsme", "jsou", "jste", "k", "kam",
    "kde", "kdo", "kdy", "když", "ke", "která", "které", "kteří", "který", "ktera", "ktere",
    "ktery", "ku", "ma", "má", "mají", "mate", "máte", "me", "mě", "mezi", "mi", "mit", "mít",
    "mne", "mně", "mnou", "moc", "muj", "můj", "musí", "muze", "může", "my", "na", "nad", "nam",
    "nám", "napiste", "napište", "nas", "nás", "náš", "ne", "nebo", "nebyl", "nebyla", "nechť",
    "nejsou", "neni", "není", "než", "nic", "nich", "nove", "nové", "novy", "nový", "nyní", "o",
    "od", "on", "ona", "oni", "ono", "ony", "pak", "po", "pod", "podle", "pokud", "pouze",
    "prave", "právě", "pred", "před", "pres", "přes", "pri", "při", "pro", "proc", "proč",
    "prosim", "prosím", "proti", "proto", "protoze", "protože", "prvni", "první", "pta", "re",
    "s", "se", "si", "sice", "skoro", "smi", "smí", "snad", "spis", "spíš", "sve", "své", "svuj",
    "svůj", "svych", "svých", "svym", "svým", "svymi", "svými", "ta", "tady", "tak", "take",
    "také", "takze", "takže", "tam", "tato", "te", "té", "tebe", "tedy", "ten", "tento", "teto",
    "této", "tim", "tím", "timto", "tímto", "to", "tobe", "tobě", "tohle", "toho", "tohoto",
    "tom", "tomto", "tomu", "tu", "tuto", "tvuj", "tvůj", "ty", "tyto", "u", "uz", "už", "v",
    "vam", "vám", "vas", "vás", "váš", "ve", "vedle", "vice", "více", "vsak", "však", "vy",
    "z", "za", "zda", "zde", "ze", "že", "jeste", "coz",
    # English chat filler
    "the", "an", "is", "it", "of", "in", "and", "or", "for", "so", "im", "i'm",
    "you", "your", "ur", "we", "he", "she", "they", "this", "that", "was", "are",
    "be", "at", "as", "but", "not", "no", "yes", "yeah", "lol", "lmao", "xd", "omg", "pls", "plz",
    "just", "like", "get", "got", "gg", "wtf", "yo", "hi", "hey", "wow", "oh", "ok", "okay",
}

# \w keeps Czech accented letters + digits + underscore (Unicode by default for str patterns),
# and splits on every other character — mentions, punctuation, emoji all become separators.
_SPLIT_RE = re.compile(r"[^\w]+", re.UNICODE)

# Distinctive-phrase lift denominator floor: a phrase never seen in the stream still gets a finite,
# large lift rather than dividing by zero.
_LIFT_EPSILON = 0.01

# Memory bounds for phrase_stats over very large streams (a 1M-message stream would otherwise grow
# the phrase->count and phrase->chatter-set maps without limit and exhaust RPI memory).
# _MAX_CHATTERS_PER_PHRASE caps each phrase's distinct-chatter set; chatter_count SATURATES at this
# value (an extremely popular phrase reports at most this many distinct chatters).
_MAX_CHATTERS_PER_PHRASE = 1024
# _PHRASE_PRUNE_THRESHOLD bounds the number of tracked phrases: once the usage map grows past it,
# singleton phrases (usage_count == 1, overwhelmingly one-off noise) are dropped, lossy-counting
# style — a dropped phrase that later recurs loses its earlier occurrence, so surviving counts are a
# lower bound (approximate). Recurring phrases, the ones that matter for the rollup, are unaffected.
_PHRASE_PRUNE_THRESHOLD = 150_000


def tokenize(text: str) -> List[str]:
    """Lowercase, drop punctuation, split on whitespace/symbols. Empty tokens removed."""
    if not text:
        return []
    return [tok for tok in _SPLIT_RE.split(text.lower()) if tok]


def _phrases(text: str, emote_names: Set[str]) -> List[str]:
    """Unigrams + bigrams for one text, stopword- and emote-filtered.

    Unigrams: token kept unless it is a stopword or a known emote name (emotes are counted
    separately). Bigrams: adjacent token pair kept only when NEITHER token is a stopword or emote.
    ``emote_names`` is expected pre-lowercased.
    """
    tokens = tokenize(text)
    phrases: List[str] = []
    for tok in tokens:
        if tok not in CZECH_STOPWORDS and tok not in emote_names:
            phrases.append(tok)
    for left, right in zip(tokens, tokens[1:], strict=False):
        if left in CZECH_STOPWORDS or right in CZECH_STOPWORDS:
            continue
        if left in emote_names or right in emote_names:
            continue
        phrases.append(f"{left} {right}")
    return phrases


def phrase_stats(
    rows: Iterable[Tuple[str, int, int]], emote_names: Set[str]
) -> Tuple[Dict[str, int], Dict[str, Set[int]]]:
    """Accumulate (usage_count dict, distinct-chatter-set dict) over (text, chatter_id, occ) rows.

    Returned once and reused for both the stored top-phrase rollup and the per-minute stream
    frequency baseline used by ``distinctive_phrases``.

    Bounded memory (see ``_MAX_CHATTERS_PER_PHRASE`` / ``_PHRASE_PRUNE_THRESHOLD``): each phrase's
    chatter set is capped (chatter_count saturates), and once the usage map exceeds the prune
    threshold its singleton phrases are dropped (lossy-counting-style approximation). Both bounds
    only affect long-tail noise on huge streams; recurring phrases are preserved.
    """
    usage: Dict[str, int] = defaultdict(int)
    chatters: Dict[str, Set[int]] = defaultdict(set)
    for text, chatter_id, occurrence_count in rows:
        for phrase, in_text in Counter(_phrases(text, emote_names)).items():
            usage[phrase] += in_text * occurrence_count
            bucket = chatters[phrase]
            if len(bucket) < _MAX_CHATTERS_PER_PHRASE:
                bucket.add(chatter_id)
        if len(usage) > _PHRASE_PRUNE_THRESHOLD:
            for phrase in [p for p, count in usage.items() if count == 1]:
                del usage[phrase]
                chatters.pop(phrase, None)
    return usage, chatters


def top_phrases(
    rows: Iterable[Tuple[str, int, int]],
    emote_names: Set[str],
    limit: int = 40,
    min_count: int = 3,
) -> List[Tuple[str, int, int]]:
    """Recurring phrases across a stream, as ``(phrase, usage_count, chatter_count)``.

    ``rows`` are ``(text, chatter_id, occurrence_count)``. Phrases below ``min_count`` total
    occurrences are dropped; the rest are ordered by usage desc then phrase asc, capped at ``limit``.
    """
    usage, chatters = phrase_stats(rows, emote_names)
    ranked = [
        (phrase, count, len(chatters[phrase]))
        for phrase, count in usage.items()
        if count >= min_count
    ]
    ranked.sort(key=lambda item: (-item[1], item[0]))
    return ranked[:limit]


def distinctive_phrases(
    window_rows: Iterable[Tuple[str, int]],
    stream_freq: Dict[str, float],
    emote_names: Set[str],
    limit: int = 5,
) -> List[Tuple[str, int, float]]:
    """Phrases most over-represented inside a moment window, as ``(phrase, window_count, lift)``.

    ``window_rows`` are ``(text, occurrence_count)`` for the window. ``stream_freq`` maps phrase to
    its whole-stream per-minute frequency; lift = window_count / max(stream_freq, epsilon). Ordered
    by lift desc, then window_count desc, then phrase asc.
    """
    window_counts: Dict[str, int] = defaultdict(int)
    for text, occurrence_count in window_rows:
        for phrase, in_text in Counter(_phrases(text, emote_names)).items():
            window_counts[phrase] += in_text * occurrence_count

    scored = [
        (phrase, count, round(count / max(stream_freq.get(phrase, 0.0), _LIFT_EPSILON), 2))
        for phrase, count in window_counts.items()
    ]
    scored.sort(key=lambda item: (-item[2], -item[1], item[0]))
    return scored[:limit]
