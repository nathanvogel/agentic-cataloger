"""Dependency graph and parity unit tests (1.2-UNIT-002/003)."""

from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
BACKEND_ROOT = REPO_ROOT / "backend"
PYPROJECT = BACKEND_ROOT / "pyproject.toml"
LOCKFILE = BACKEND_ROOT / "uv.lock"
DEVCONTAINER = REPO_ROOT / ".devcontainer" / "devcontainer.json"
CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "backend.yml"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


def test_unit_002_no_redis_or_external_workflow_runtime() -> None:
    lock = LOCKFILE.read_text()
    forbidden = ("redis", "celery", "langgraph-cli", "langgraph-server")
    for name in forbidden:
        assert name not in lock.lower()


def test_unit_003_devcontainer_ci_postgres_and_role_parity() -> None:
    compose = yaml.safe_load(COMPOSE_FILE.read_text())
    assert compose["services"]["postgres"]["image"] == "postgres:18.4"

    devcontainer = json.loads(DEVCONTAINER.read_text())
    compose_ref = devcontainer["dockerComposeFile"]
    assert "docker-compose.yml" in compose_ref

    workflow = CI_WORKFLOW.read_text()
    assert "postgres:18.4" in workflow
    assert "pricecomp migrate" in workflow
    assert "pricecomp api" in workflow or "uv run pricecomp api" in workflow
