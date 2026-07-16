"""Dependency-direction checks for framework-neutral application code."""

import ast
from pathlib import Path


def test_application_layer_does_not_import_transport_adapters() -> None:
    application_root = Path(__file__).parents[3] / "stream_sniper" / "application"
    violations: list[str] = []

    for path in sorted(application_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                forbidden_relative = node.level >= 2 and module.startswith(("api", "collector"))
                forbidden_absolute = module.startswith(("stream_sniper.api", "stream_sniper.collector"))
                if forbidden_relative or forbidden_absolute:
                    violations.append(f"{path.relative_to(application_root)}:{node.lineno}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(("stream_sniper.api", "stream_sniper.collector")):
                        violations.append(f"{path.relative_to(application_root)}:{node.lineno}")

    assert violations == []


def test_database_layer_does_not_import_api_policy() -> None:
    database_root = Path(__file__).parents[3] / "stream_sniper" / "database"
    violations: list[str] = []

    for path in sorted(database_root.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if (node.level >= 2 and module.startswith("api")) or module.startswith("stream_sniper.api"):
                    violations.append(f"{path.relative_to(database_root)}:{node.lineno}")
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("stream_sniper.api"):
                        violations.append(f"{path.relative_to(database_root)}:{node.lineno}")

    assert violations == []
