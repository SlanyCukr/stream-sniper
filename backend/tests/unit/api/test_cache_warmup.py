"""Cache warm-up reports partial failures to its runtime-owned boundary."""

from unittest.mock import Mock, call

import pytest

from stream_sniper.api.caching.cache_warmup import warm_cache


def test_warm_cache_attempts_every_entry_then_raises_partial_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    cache = Mock()
    cache.generate_key.side_effect = lambda *parts: ":".join(map(str, parts))
    cache.set.return_value = True
    counts = Mock(side_effect=[10, RuntimeError("creator one failed"), 20, RuntimeError("creator three failed")])
    monkeypatch.setattr("stream_sniper.api.caching.cache_warmup.select_creators_db", Mock(return_value=[]))
    monkeypatch.setattr("stream_sniper.api.caching.cache_warmup.count_streams_db", counts)

    with pytest.raises(ExceptionGroup) as raised:
        warm_cache(cache)

    assert counts.call_args_list == [call(-1), call(1), call(2), call(3)]
    assert [str(error) for error in raised.value.exceptions] == ["creator one failed", "creator three failed"]
