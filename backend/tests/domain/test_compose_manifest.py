"""Static compose manifest tests (1.2-UNIT-001)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"

FORBIDDEN_TOKENS = (
    "legacy/",
    "5532",
    "pricecomp_db",
    "legacy/docker-compose",
)


@pytest.mark.parametrize("token", FORBIDDEN_TOKENS)
def test_unit_001_compose_has_no_legacy_references(token: str) -> None:
    """Root compose must not reference legacy paths or frozen ports."""
    content = COMPOSE_FILE.read_text()
    assert token not in content


def test_unit_001_postgres_image_pinned() -> None:
    """Postgres service image stays pinned to 18.4."""
    compose = yaml.safe_load(COMPOSE_FILE.read_text())
    assert compose["services"]["postgres"]["image"] == "postgres:18.4"
