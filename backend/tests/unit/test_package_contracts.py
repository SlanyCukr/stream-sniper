"""Import contracts for intentionally public package surfaces."""

import ast
import importlib
import re
import tomllib
from pathlib import Path

import stream_sniper
import stream_sniper.collector as collector_package
import stream_sniper.database as database_package
import stream_sniper.tracking as tracking_package


def test_root_package_exports_only_installed_version() -> None:
    assert stream_sniper.__all__ == ["__version__"]
    assert stream_sniper.__version__
    assert not hasattr(stream_sniper, "TwitchCollectorFacade")
    assert not hasattr(stream_sniper, "app")


def test_implementation_packages_do_not_eagerly_export_facades_or_gateways() -> None:
    assert not hasattr(collector_package, "TwitchCollectorFacade")
    assert not hasattr(database_package, "select_creators_db")
    assert not hasattr(database_package, "with_cursor")
    assert not hasattr(tracking_package, "TrackingScheduler")


def test_concrete_modules_remain_directly_importable() -> None:
    modules = (
        "stream_sniper.collector.archived.twitch_collector_facade",
        "stream_sniper.database.gateways.identity.creator_table_gateway",
        "stream_sniper.database.core.decorators",
        "stream_sniper.api.server",
    )
    assert all(importlib.import_module(name) for name in modules)


def test_api_root_is_a_small_composition_boundary() -> None:
    backend_root = Path(__file__).parents[2]
    api_root = backend_root / "stream_sniper/api"

    assert {path.name for path in api_root.glob("*.py")} == {
        "__init__.py",
        "api.py",
        "asgi.py",
        "config.py",
        "dependencies.py",
        "error_boundary.py",
        "middleware.py",
        "runtime.py",
        "server.py",
    }


def test_api_infrastructure_has_explicit_package_ownership() -> None:
    backend_root = Path(__file__).parents[2]
    api_root = backend_root / "stream_sniper/api"
    expected_modules = {
        "caching": {"__init__.py", "cache.py", "cache_warmup.py", "model_cache.py", "rollup_version.py"},
        "observability": {"__init__.py", "health.py", "health_contracts.py", "health_renderers.py", "monitoring.py"},
        "security": {"__init__.py", "auth.py", "auth_models.py", "rate_limiter.py"},
        "transport": {"__init__.py", "export_utils.py", "models.py"},
    }

    for package, module_names in expected_modules.items():
        assert {path.name for path in (api_root / package).glob("*.py")} == module_names


def test_tracking_contracts_are_application_owned() -> None:
    backend_root = Path(__file__).parents[2]
    persistence_records = backend_root / "stream_sniper/database/gateways/tracking/records.py"
    assert not persistence_records.exists()

    for source_path in (backend_root / "stream_sniper").rglob("*.py"):
        assert "database.gateways.tracking.records" not in source_path.read_text()


def test_multi_gateway_tracking_workflow_is_not_owned_by_transport() -> None:
    backend_root = Path(__file__).parents[2]
    endpoint_source = (backend_root / "stream_sniper/api/features/tracking/tracking_job_endpoints.py").read_text()
    workflow_source = (backend_root / "stream_sniper/application/tracking/manual_processing.py").read_text()

    assert "stream_table_gateway" not in endpoint_source
    assert "tracked_streamers_table_gateway" not in endpoint_source
    assert "stream_table_gateway" in workflow_source
    assert "tracked_streamers_table_gateway" in workflow_source


def test_analytics_modules_are_grouped_by_change_boundary() -> None:
    backend_root = Path(__file__).parents[2]
    analytics_root = backend_root / "stream_sniper/analytics"

    assert {path.name for path in analytics_root.glob("*.py")} == {"__init__.py"}
    expected_modules = {
        "calculations": {"__init__.py", "moments.py", "report_stats.py", "text_stats.py"},
        "operations": {"__init__.py", "backfill.py", "bot_detection.py", "digest.py"},
        "rollups": {
            "__init__.py",
            "community.py",
            "emote_seed.py",
            "moment_enrichment.py",
            "rollup_engine.py",
            "scene_events.py",
        },
    }
    for package, module_names in expected_modules.items():
        assert {path.name for path in (analytics_root / package).glob("*.py")} == module_names


def test_all_documented_console_entry_points_are_importable() -> None:
    backend_root = Path(__file__).parents[2]
    pyproject_path = backend_root / "pyproject.toml"
    scripts = tomllib.loads(pyproject_path.read_text())["project"]["scripts"]
    contributor_guide = (backend_root / "CLAUDE.md").read_text()

    for target in scripts.values():
        module_name, attribute_name = target.split(":", maxsplit=1)
        module = importlib.import_module(module_name)
        assert callable(getattr(module, attribute_name))
        assert target in contributor_guide

    assert "collector/archived/database_buffer.py" in contributor_guide


def test_production_mypy_has_no_module_exemptions() -> None:
    """Keep the full production package inside the same strict mypy contract."""
    pyproject_path = Path(__file__).parents[2] / "pyproject.toml"
    mypy_config = tomllib.loads(pyproject_path.read_text())["tool"]["mypy"]

    assert "overrides" not in mypy_config


def test_application_has_no_fastapi_dependency() -> None:
    backend_root = Path(__file__).parents[2]
    application_root = backend_root / "stream_sniper/application"
    for source_path in application_root.rglob("*.py"):
        tree = ast.parse(source_path.read_text())
        imports = [node.module or "" for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)] + [
            alias.name for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names
        ]
        assert not any(module == "fastapi" or module.startswith("fastapi.") for module in imports)


def test_cross_gateway_http_handlers_delegate_to_application() -> None:
    backend_root = Path(__file__).parents[2]
    feature_root = backend_root / "stream_sniper/api/features"
    for relative_path in (
        "community/community_endpoints.py",
        "creators/analytics_endpoints.py",
        "streams/compare_endpoints.py",
        "streams/stream_report_endpoints.py",
        "streams/timeline_endpoints.py",
        "tracking/tracking_job_endpoints.py",
    ):
        source = (feature_root / relative_path).read_text()
        assert "application." in source
        assert "database.gateways" not in source


def test_collector_root_separates_archived_and_live_pipelines() -> None:
    backend_root = Path(__file__).parents[2]
    collector_root = backend_root / "stream_sniper/collector"

    # Root holds only the seams both pipelines share: the Twitch client and the
    # canonical badge-text formatter (archived + live must emit identical badge text).
    assert {path.name for path in collector_root.glob("*.py")} == {
        "__init__.py",
        "badge_format.py",
        "twitch_api.py",
    }
    assert {path.name for path in (collector_root / "archived").glob("*.py")} == {
        "__init__.py",
        "archived_stream.py",
        "chat_parser.py",
        "creator_resolver.py",
        "database_buffer.py",
        "message_rows.py",
        "twitch_archived_chat.py",
        "twitch_collector_facade.py",
        "twitch_vod_chat_downloader.py",
        "vod_ingestion.py",
    }


def test_tracking_schema_snapshot_matches_current_job_contract() -> None:
    backend_root = Path(__file__).parents[2]
    snapshot = (backend_root / "stream_sniper/database/create_table.sql").read_text()
    tracking_doc = (backend_root.parent / "TRACKING_SYSTEM.md").read_text()

    for current_name in (
        "last_processed_vod_id",
        "twitch_vod_id",
        "worker_token",
        "lease_expires_at",
        "cancellation_requested_at",
        "processing_jobs_streamer_vod_uq",
        "processing_jobs_dispatch_idx",
    ):
        assert current_name in snapshot
    assert "last_processed_stream_id" not in snapshot
    assert "twitch_stream_id" not in snapshot
    assert "Alembic migrations are the authoritative schema definition" in tracking_doc
    assert "CREATE TABLE stream_sniper.processing_jobs" not in tracking_doc


def _top_level_mapping_keys(document: str, section: str) -> set[str]:
    match = re.search(
        rf"(?ms)^{section}:\n(?P<body>.*?)(?=^[a-zA-Z0-9_-]+:\s*$)",
        document,
    )
    assert match is not None
    return set(re.findall(r"(?m)^  ([a-zA-Z0-9_-]+):\s*$", match.group("body")))


def test_architecture_runbooks_match_packages_and_dev_compose_services() -> None:
    backend_root = Path(__file__).parents[2]
    repository_root = backend_root.parent
    root_runbook = (repository_root / "CLAUDE.md").read_text()
    backend_runbook = (backend_root / "CLAUDE.md").read_text()
    compose = (repository_root / "docker-compose.yml").read_text()

    expected_packages = {"analytics", "api", "application", "collector", "database", "tracking", "utils"}
    package_directories = {
        path.name
        for path in (backend_root / "stream_sniper").iterdir()
        if path.is_dir() and (path / "__init__.py").is_file()
    }
    assert package_directories == expected_packages
    assert all(f"`{package}/`" in root_runbook for package in expected_packages)
    assert all(f"**`{package}/`**" in backend_runbook for package in expected_packages)
    assert "`auth/`" not in root_runbook

    compose_services = _top_level_mapping_keys(compose, "services")
    assert compose_services == {"api", "collector", "frontend", "live"}
    assert "docker-compose up api|frontend|collector|live" in root_runbook
    assert "docker-compose logs -f api|frontend|collector|live" in root_runbook
