"""Contract tests for runtime-resource dependency mappings."""

from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request

from stream_sniper.api import dependencies


@pytest.mark.parametrize(
    ("accessor", "owner", "attribute"),
    [
        (dependencies.get_config, "app", "config"),
        (dependencies.get_cache, "runtime", "cache"),
        (dependencies.get_metrics_collector, "runtime", "metrics"),
        (dependencies.get_health_checker, "runtime", "health"),
        (dependencies.get_twitch_client, "runtime", "twitch"),
    ],
)
def test_accessor_maps_to_exact_composed_resource(accessor, owner, attribute):
    sentinel = object()
    app = FastAPI()
    app.state.config = sentinel if owner == "app" else object()
    app.state.runtime = SimpleNamespace(
        cache=sentinel if attribute == "cache" else object(),
        metrics=sentinel if attribute == "metrics" else object(),
        health=sentinel if attribute == "health" else object(),
        twitch=sentinel if attribute == "twitch" else object(),
    )
    request = Request({"type": "http", "app": app, "headers": []})

    assert accessor(request) is sentinel
