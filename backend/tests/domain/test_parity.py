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
CI_SCRIPT = REPO_ROOT / "scripts" / "ci" / "backend-test.sh"
COMPOSE_FILE = REPO_ROOT / "docker-compose.yml"


def test_unit_002_no_redis_or_external_workflow_runtime() -> None:
    """Lockfile must not pull Redis, Celery, or LangGraph Server/CLI."""
    lock = LOCKFILE.read_text()
    forbidden = ("redis", "celery", "langgraph-cli", "langgraph-server")
    for name in forbidden:
        assert name not in lock.lower()


def _load_jsonc(path: Path) -> object:
    """Parse JSONC (devcontainer allows // comments)."""
    lines = []
    for line in path.read_text().splitlines():
        stripped = line.lstrip()
        if stripped.startswith("//"):
            continue
        lines.append(line)
    return json.loads("\n".join(lines))


def test_unit_003_devcontainer_ci_postgres_and_role_parity() -> None:
    """Devcontainer, CI, and compose agree on Postgres 18.4 and role commands."""
    compose = yaml.safe_load(COMPOSE_FILE.read_text())
    assert compose["services"]["postgres"]["image"] == "postgres:18.4"

    devcontainer = _load_jsonc(DEVCONTAINER)
    assert isinstance(devcontainer, dict)
    compose_ref = devcontainer["dockerComposeFile"]
    assert "docker-compose.yml" in str(compose_ref)

    workflow = CI_WORKFLOW.read_text()
    assert "postgres:18.4" in workflow
    assert "./scripts/ci/backend-test.sh" in workflow

    ci_script = CI_SCRIPT.read_text()
    assert "agentic-cataloger migrate" in ci_script
    assert "pytest tests/integration" in ci_script
