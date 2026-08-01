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
    for name in SEED_PACKAGES:
        module = importlib.import_module(name)
        assert module is not None


def test_retrieval_package_absent() -> None:
    retrieval = BACKEND_ROOT / "src" / "pricecomp" / "retrieval"
    assert not retrieval.exists()


def test_migrations_and_test_dirs_exist() -> None:
    assert (BACKEND_ROOT / "migrations").is_dir()
    for name in ("domain", "integration", "contract", "evals"):
        assert (BACKEND_ROOT / "tests" / name).is_dir()
