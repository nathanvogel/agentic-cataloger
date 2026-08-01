"""Process-spawn tests for role commands (1.2-PROC-001/002/003)."""

from __future__ import annotations

import os
import signal
import time

import pytest

from tests.conftest import spawn_role, wait_for_http


@pytest.mark.proc
def test_proc_001_migrate_exits_zero(migrate_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MIGRATE_DATABASE_URL", migrate_url)
    proc = spawn_role("migrate")
    stdout, stderr = proc.communicate(timeout=120)
    assert proc.returncode == 0, stderr or stdout


@pytest.mark.proc
def test_proc_002_worker_starts_and_stops(
    app_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", app_database_url)
    proc = spawn_role("worker")
    time.sleep(1.0)
    assert proc.poll() is None
    proc.send_signal(signal.SIGTERM)
    stdout, stderr = proc.communicate(timeout=10)
    assert proc.returncode == 0, stderr or stdout


@pytest.mark.proc
def test_proc_003_api_health_on_3020(
    migrated_database: str,
    app_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("DATABASE_URL", app_database_url)
    proc = spawn_role("api")
    try:
        wait_for_http("http://127.0.0.1:3020/health")
        wait_for_http("http://127.0.0.1:3020/ready")
    finally:
        proc.send_signal(signal.SIGTERM)
        proc.communicate(timeout=10)
