"""Structural seed smoke tests — packages exist and import; no domain logic yet."""

from __future__ import annotations

import importlib
from pathlib import Path

SEED_PACKAGES = (
    "pricecomp",
    "pricecomp.contracts",
    "pricecomp.catalog",
    "pricecomp.taxonomy",
    "pricecomp.enrichment",
    "pricecomp.review",
    "pricecomp.pipeline",
    "pricecomp.comparison",
    "pricecomp.evaluation",
    "pricecomp.platform",
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
