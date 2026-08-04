"""Process-spawn tests for role commands (1.2-PROC-001/002/003)."""

from __future__ import annotations

import signal
import time

import pytest
from tests.conftest import resolve_api_test_port, spawn_role, wait_for_http


@pytest.mark.proc
def test_proc_001_migrate_exits_zero(
    migrate_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Spawned `agentic-cataloger migrate` exits 0 on a ready database."""
    monkeypatch.setenv("MIGRATE_DATABASE_URL", migrate_url)
    proc = spawn_role("migrate")
    stdout, stderr = proc.communicate(timeout=120)
    assert proc.returncode == 0, stderr or stdout


@pytest.mark.proc
def test_proc_002_worker_starts_and_stops(
    app_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spawned worker stays up until SIGTERM, then exits 0."""
    monkeypatch.setenv("DATABASE_URL", app_database_url)
    proc = spawn_role("worker")
    time.sleep(1.0)
    assert proc.poll() is None
    proc.send_signal(signal.SIGTERM)
    stdout, stderr = proc.communicate(timeout=10)
    assert proc.returncode == 0, stderr or stdout


@pytest.mark.proc
def test_proc_003_api_health(
    migrated_database: str,
    app_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Spawned API serves `/health` and `/ready` on a dedicated port."""
    port = resolve_api_test_port()
    monkeypatch.setenv("DATABASE_URL", app_database_url)
    monkeypatch.setenv("API_PORT", str(port))
    proc = spawn_role("api")
    try:
        time.sleep(0.5)
        if proc.poll() is not None:
            stdout, stderr = proc.communicate(timeout=1)
            pytest.fail(f"API process exited early: {stderr or stdout}")
        base = f"http://127.0.0.1:{port}"
        wait_for_http(f"{base}/health")
        wait_for_http(f"{base}/ready")
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=10)
