"""Structural seed smoke tests — packages exist and import; no domain logic yet."""

from __future__ import annotations

import importlib
from pathlib import Path

SEED_PACKAGES = (
    "agentic_cataloger",
    "agentic_cataloger.contracts",
    "agentic_cataloger.catalog",
    "agentic_cataloger.taxonomy",
    "agentic_cataloger.enrichment",
    "agentic_cataloger.review",
    "agentic_cataloger.pipeline",
    "agentic_cataloger.comparison",
    "agentic_cataloger.evaluation",
    "agentic_cataloger.platform",
)

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_seed_packages_import() -> None:
    """Seed domain packages import without raising."""
    for name in SEED_PACKAGES:
        module = importlib.import_module(name)
        assert module is not None


def test_migrations_and_test_dirs_exist() -> None:
    """Migrations and expected test suite directories exist."""
    assert (BACKEND_ROOT / "migrations").is_dir()
    for name in ("domain", "integration", "contract", "evals"):
        assert (BACKEND_ROOT / "tests" / name).is_dir()
