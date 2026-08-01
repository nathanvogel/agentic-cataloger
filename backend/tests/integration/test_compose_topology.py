"""Compose topology and Phoenix settings tests (1.2-INT-005/006/007/010)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


@pytest.fixture
def compose() -> dict:
    return yaml.safe_load(COMPOSE_FILE.read_text())


def test_int_005_postgres_port_3021(compose: dict) -> None:
    ports = compose["services"]["postgres"]["ports"]
    assert "3021:5432" in ports


def test_int_006_phoenix_port_3022(compose: dict) -> None:
    ports = compose["services"]["phoenix"]["ports"]
    assert "3022:6006" in ports


def test_int_007_api_port_3020(compose: dict) -> None:
    ports = compose["services"]["api"]["ports"]
    assert "3020:3020" in ports


def test_int_010_phoenix_retention_and_telemetry(compose: dict) -> None:
    env = compose["services"]["phoenix"]["environment"]
    assert env["PHOENIX_DEFAULT_RETENTION_POLICY_DAYS"] == "30"
    assert env["PHOENIX_TELEMETRY_ENABLED"] == "false"
