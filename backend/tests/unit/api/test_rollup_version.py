"""Rollup-version cache-key helpers: passthrough, sentinel, and resilience."""

import pytest

from stream_sniper.api.caching import rollup_version


@pytest.mark.parametrize(
    ("helper", "gateway_name", "args"),
    [
        (rollup_version.stream_rollup_version, "select_stream_rollup_version_db", (42,)),
        (rollup_version.stream_creator_rollup_version, "select_stream_creator_rollup_version_db", (42,)),
        (rollup_version.creator_rollup_version, "select_creator_rollup_version_db", (7,)),
    ],
)
def test_version_passes_through_gateway_value(monkeypatch, helper, gateway_name, args):
    monkeypatch.setattr(rollup_version, gateway_name, lambda _id: "1752756000.123456")
    assert helper(*args) == "1752756000.123456"


def test_scene_version_passes_through_gateway_value(monkeypatch):
    monkeypatch.setattr(rollup_version, "select_scene_rollup_version_db", lambda: "1752756000.5")
    assert rollup_version.scene_rollup_version() == "1752756000.5"


def test_missing_rollup_yields_the_unversioned_sentinel(monkeypatch):
    monkeypatch.setattr(rollup_version, "select_stream_rollup_version_db", lambda _id: None)
    assert rollup_version.stream_rollup_version(42) == "unversioned"


def test_probe_failure_degrades_to_the_sentinel_instead_of_raising(monkeypatch):
    def boom(_id):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(rollup_version, "select_creator_rollup_version_db", boom)
    assert rollup_version.creator_rollup_version(7) == "unversioned"
