"""Shared pytest fixtures for integration and PROC tests.

Closes TECH-002: disposable PostgreSQL 18.4, process-spawn/kill harness for PROC
scenarios (Story 1.3 single-writer, GATE-03 P4 SIGKILL).

Prefers testcontainers when Docker is available; otherwise uses the compose/CI
Postgres service (PRICECOMP_TEST_PG_* or host ``postgres``).
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
from collections.abc import Generator, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Union

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
POSTGRES_IMAGE = "postgres:18.4"
MIGRATE_SUPERUSER = "postgresql://postgres:{password}@{host}:{port}/pricecomp_app"
APP_RUNTIME = "postgresql://pricecomp_app:pricecomp_app_dev@{host}:{port}/pricecomp_app"
PHOENIX_RUNTIME = (
    "postgresql://pricecomp_phoenix:pricecomp_phoenix_dev@{host}:{port}/pricecomp_phoenix"
)

PostgresHandle = Union[PostgresContainer, "ExternalPostgres"]


@dataclass(frozen=True)
class ExternalPostgres:
    """Compose/CI Postgres stand-in with the same port accessor as testcontainers."""

    host: str
    port: int
    password: str = "postgres"

    def get_exposed_port(self, _container_port: int) -> str:
        return str(self.port)


def bootstrap_gate02_roles(
    port: int,
    *,
    host: str = "localhost",
    password: str = "test",
) -> None:
    """Mirror docker/postgres/init/01-roles.sql without psql meta-commands."""
    admin = f"postgresql://postgres:{password}@{host}:{port}/postgres"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute("CREATE ROLE pricecomp_app LOGIN PASSWORD 'pricecomp_app_dev'")
        conn.execute(
            "CREATE ROLE pricecomp_phoenix LOGIN PASSWORD 'pricecomp_phoenix_dev'"
        )
        conn.execute("CREATE DATABASE pricecomp_app")
        conn.execute("CREATE DATABASE pricecomp_phoenix OWNER pricecomp_phoenix")
        conn.execute("REVOKE ALL ON DATABASE pricecomp_app FROM PUBLIC")
        conn.execute("REVOKE ALL ON DATABASE pricecomp_phoenix FROM PUBLIC")
        conn.execute("GRANT CONNECT ON DATABASE pricecomp_app TO pricecomp_app")
        conn.execute("GRANT CONNECT ON DATABASE pricecomp_phoenix TO pricecomp_phoenix")

    app_admin = f"postgresql://postgres:{password}@{host}:{port}/pricecomp_app"
    with psycopg.connect(app_admin, autocommit=True) as conn:
        conn.execute("GRANT USAGE ON SCHEMA public TO pricecomp_app")
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO pricecomp_app"
        )
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO pricecomp_app"
        )

    phoenix_admin = f"postgresql://postgres:{password}@{host}:{port}/pricecomp_phoenix"
    with psycopg.connect(phoenix_admin, autocommit=True) as conn:
        conn.execute("GRANT ALL ON SCHEMA public TO pricecomp_phoenix")
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO pricecomp_phoenix"
        )
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL ON SEQUENCES TO pricecomp_phoenix"
        )


def _run_init_sql(port: int, *, host: str = "localhost", password: str = "test") -> None:
    bootstrap_gate02_roles(port, host=host, password=password)


def _docker_available() -> bool:
    try:
        import docker

        client = docker.from_env()
        client.ping()
        client.close()
        return True
    except Exception:  # noqa: BLE001 — any failure means use external Postgres
        return False


def _external_postgres_from_env() -> ExternalPostgres | None:
    """Use compose/CI Postgres when Docker is unavailable or explicitly requested."""
    forced = os.environ.get("PRICECOMP_TEST_PG_HOST")
    if forced:
        return ExternalPostgres(
            host=forced,
            port=int(os.environ.get("PRICECOMP_TEST_PG_PORT", "5432")),
            password=os.environ.get("PRICECOMP_TEST_PG_PASSWORD", "postgres"),
        )
    if _docker_available():
        return None
    # Devcontainer / compose network default.
    return ExternalPostgres(host="postgres", port=5432, password="postgres")


def _connection_parts(handle: PostgresHandle) -> tuple[str, int, str]:
    if isinstance(handle, ExternalPostgres):
        return handle.host, handle.port, handle.password
    return "localhost", int(handle.get_exposed_port(5432)), "test"


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresHandle, None, None]:
    external = _external_postgres_from_env()
    if external is not None:
        yield external
        return

    with PostgresContainer(POSTGRES_IMAGE, username="postgres", password="test") as postgres:
        port = int(postgres.get_exposed_port(5432))
        _run_init_sql(port)
        yield postgres


@pytest.fixture
def migrate_url(postgres_container: PostgresHandle) -> str:
    host, port, password = _connection_parts(postgres_container)
    return MIGRATE_SUPERUSER.format(host=host, port=port, password=password)


@pytest.fixture
def app_database_url(postgres_container: PostgresHandle) -> str:
    host, port, _password = _connection_parts(postgres_container)
    return APP_RUNTIME.format(host=host, port=port)


@pytest.fixture
def phoenix_database_url(postgres_container: PostgresHandle) -> str:
    host, port, _password = _connection_parts(postgres_container)
    return PHOENIX_RUNTIME.format(host=host, port=port)


@pytest.fixture
def migrated_database(
    migrate_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[str]:
    monkeypatch.setenv("MIGRATE_DATABASE_URL", migrate_url)
    from pricecomp.platform.roles.migrate import run_migrate

    assert run_migrate() == 0
    yield migrate_url


def spawn_role(
    role: str,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[str]:
    """Spawn a `pricecomp <role>` process for PROC-level tests."""
    merged = os.environ.copy()
    if env:
        merged.update(env)
    pricecomp = BACKEND_ROOT / ".venv" / "bin" / "pricecomp"
    command = [str(pricecomp), role] if pricecomp.exists() else [
        sys.executable,
        "-m",
        "pricecomp.platform.cli",
        role,
    ]
    return subprocess.Popen(
        command,
        cwd=BACKEND_ROOT,
        env=merged,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def terminate_role(
    proc: subprocess.Popen[str],
    *,
    timeout_s: float = 10.0,
) -> tuple[int | None, str, str]:
    """SIGTERM a spawned role and wait for exit. Returns (code, stdout, stderr)."""
    if proc.poll() is None:
        proc.send_signal(signal.SIGTERM)
    stdout, stderr = proc.communicate(timeout=timeout_s)
    return proc.returncode, stdout, stderr


def kill_role(
    proc: subprocess.Popen[str],
    *,
    timeout_s: float = 10.0,
) -> tuple[int | None, str, str]:
    """SIGKILL a spawned role (GATE-03 P4). Returns (code, stdout, stderr)."""
    if proc.poll() is None:
        proc.send_signal(signal.SIGKILL)
    stdout, stderr = proc.communicate(timeout=timeout_s)
    return proc.returncode, stdout, stderr


def wait_for_http(url: str, *, timeout_s: float = 10.0) -> None:
    deadline = time.time() + timeout_s
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            import urllib.request

            with urllib.request.urlopen(url, timeout=1) as response:  # noqa: S310
                if response.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.2)
    raise TimeoutError(f"HTTP not ready at {url}: {last_error}")
