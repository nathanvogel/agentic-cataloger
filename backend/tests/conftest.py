"""Shared pytest fixtures for integration and PROC tests."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from collections.abc import Generator, Iterator
from pathlib import Path

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
POSTGRES_IMAGE = "postgres:18.4"
MIGRATE_SUPERUSER = "postgresql://postgres:test@localhost:{port}/pricecomp_app"
APP_RUNTIME = "postgresql://pricecomp_app:pricecomp_app_dev@localhost:{port}/pricecomp_app"
PHOENIX_RUNTIME = (
    "postgresql://pricecomp_phoenix:pricecomp_phoenix_dev@localhost:{port}/pricecomp_phoenix"
)


def bootstrap_gate02_roles(port: int, *, password: str = "test") -> None:
    """Mirror docker/postgres/init/01-roles.sql without psql meta-commands."""
    admin = f"postgresql://postgres:{password}@localhost:{port}/postgres"
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

    app_admin = f"postgresql://postgres:{password}@localhost:{port}/pricecomp_app"
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

    phoenix_admin = f"postgresql://postgres:{password}@localhost:{port}/pricecomp_phoenix"
    with psycopg.connect(phoenix_admin, autocommit=True) as conn:
        conn.execute("GRANT ALL ON SCHEMA public TO pricecomp_phoenix")
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO pricecomp_phoenix"
        )
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL ON SEQUENCES TO pricecomp_phoenix"
        )


def _run_init_sql(port: int) -> None:
    bootstrap_gate02_roles(port)


@pytest.fixture(scope="session")
def postgres_container() -> Generator[PostgresContainer, None, None]:
    with PostgresContainer(POSTGRES_IMAGE, username="postgres", password="test") as postgres:
        port = int(postgres.get_exposed_port(5432))
        _run_init_sql(port)
        yield postgres


@pytest.fixture
def migrate_url(postgres_container: PostgresContainer) -> str:
    port = int(postgres_container.get_exposed_port(5432))
    return MIGRATE_SUPERUSER.format(port=port)


@pytest.fixture
def app_database_url(postgres_container: PostgresContainer) -> str:
    port = int(postgres_container.get_exposed_port(5432))
    return APP_RUNTIME.format(port=port)


@pytest.fixture
def phoenix_database_url(postgres_container: PostgresContainer) -> str:
    port = int(postgres_container.get_exposed_port(5432))
    return PHOENIX_RUNTIME.format(port=port)


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
    timeout_s: float = 5.0,
) -> subprocess.Popen[str]:
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


def wait_for_http(url: str, *, timeout_s: float = 10.0) -> None:
    import urllib.error
    import urllib.request

    deadline = time.time() + timeout_s
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:  # noqa: S310
                if response.status < 500:
                    return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(0.2)
    raise TimeoutError(f"HTTP not ready at {url}: {last_error}")
