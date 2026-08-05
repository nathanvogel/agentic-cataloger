"""Shared pytest fixtures for integration and PROC tests.

Closes TECH-002: disposable PostgreSQL 18.4, process-spawn/kill harness for PROC
scenarios (Story 1.3 single-writer, GATE-03 P4 SIGKILL).

Prefers testcontainers when a Docker daemon is reachable; otherwise falls back to
dedicated ``*_test`` databases on an external Postgres (compose ``postgres:5432``
or host ``localhost:3021``) so the suite does not mutate the live app DBs.
"""

from __future__ import annotations

import os
import select
import signal
import socket
import subprocess
import sys
import time
from collections.abc import Generator, Iterator
from dataclasses import dataclass
from pathlib import Path

import psycopg
import pytest
from psycopg import sql

BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
POSTGRES_IMAGE = "postgres:18.4"
APP_PASSWORD = "agentic_cataloger_app_dev"
PHOENIX_PASSWORD = "agentic_cataloger_phoenix_dev"
APP_DB = "agentic_cataloger_app"
PHOENIX_DB = "agentic_cataloger_phoenix"
APP_DB_TEST = "agentic_cataloger_app_test"
PHOENIX_DB_TEST = "agentic_cataloger_phoenix_test"


@dataclass(frozen=True)
class PostgresHarness:
    """Host/port/password/database names for integration fixtures."""

    host: str
    port: int
    password: str
    app_database: str = APP_DB
    phoenix_database: str = PHOENIX_DB

    def url(self, user: str, password: str, database: str) -> str:
        """Build a libpq URL for this harness endpoint."""
        return f"postgresql://{user}:{password}@{self.host}:{self.port}/{database}"

    @property
    def migrate_url(self) -> str:
        """Superuser URL for migrate against the app database under test."""
        return self.url("postgres", self.password, self.app_database)

    @property
    def app_url(self) -> str:
        """Runtime app-role URL for the app database under test."""
        return self.url("agentic_cataloger_app", APP_PASSWORD, self.app_database)

    @property
    def phoenix_url(self) -> str:
        """Runtime Phoenix-role URL for the Phoenix database under test."""
        return self.url(
            "agentic_cataloger_phoenix", PHOENIX_PASSWORD, self.phoenix_database
        )

    @property
    def app_on_phoenix_url(self) -> str:
        """App role pointed at the Phoenix DB under test (must be denied)."""
        return self.url("agentic_cataloger_app", APP_PASSWORD, self.phoenix_database)


def bootstrap_gate02_roles(host: str, port: int, *, password: str = "test") -> None:
    """Mirror docker/postgres/init/01-roles.sql without psql meta-commands."""
    admin = f"postgresql://postgres:{password}@{host}:{port}/postgres"
    with psycopg.connect(admin, autocommit=True) as conn:
        conn.execute(
            f"CREATE ROLE agentic_cataloger_app LOGIN PASSWORD '{APP_PASSWORD}'"
        )
        conn.execute(
            f"CREATE ROLE agentic_cataloger_phoenix LOGIN PASSWORD '{PHOENIX_PASSWORD}'"
        )
        _create_database(conn, APP_DB)
        _create_database(conn, PHOENIX_DB, owner="agentic_cataloger_phoenix")
        _apply_database_connect_grants(conn, APP_DB, PHOENIX_DB)

    _grant_app_schema_privileges(host, port, password, APP_DB)
    _grant_phoenix_schema_privileges(host, port, password, PHOENIX_DB)


def ensure_external_test_databases(harness: PostgresHarness) -> None:
    """Recreate isolated ``*_test`` DBs on shared Postgres; leave live DBs alone.

    Drops and recreates each session so a leftover Alembic head from another
    branch cannot break migrate.
    """
    admin = harness.url("postgres", harness.password, "postgres")
    with psycopg.connect(admin, autocommit=True) as conn:
        for role in ("agentic_cataloger_app", "agentic_cataloger_phoenix"):
            row = conn.execute(
                "SELECT 1 FROM pg_roles WHERE rolname = %s", (role,)
            ).fetchone()
            if row is None:
                msg = (
                    f"GATE-02 role {role!r} missing on {harness.host}:{harness.port} — "
                    "run compose init or ./scripts/ci/backend-test.sh first"
                )
                raise RuntimeError(msg)

        _drop_database(conn, harness.app_database)
        _drop_database(conn, harness.phoenix_database)
        _create_database(conn, harness.app_database)
        _create_database(
            conn, harness.phoenix_database, owner="agentic_cataloger_phoenix"
        )
        _apply_database_connect_grants(
            conn, harness.app_database, harness.phoenix_database
        )

    _grant_app_schema_privileges(
        harness.host, harness.port, harness.password, harness.app_database
    )
    _grant_phoenix_schema_privileges(
        harness.host, harness.port, harness.password, harness.phoenix_database
    )


def _drop_database(conn: psycopg.Connection, name: str) -> None:
    """Drop ``name`` if it exists. Refuses names that do not end with ``_test``."""
    if not name.endswith("_test"):
        msg = f"refusing to drop non-test database {name!r}"
        raise RuntimeError(msg)
    exists = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
    ).fetchone()
    if exists is None:
        return
    conn.execute(sql.SQL("DROP DATABASE {} WITH (FORCE)").format(sql.Identifier(name)))


def _create_database(
    conn: psycopg.Connection,
    name: str,
    *,
    owner: str | None = None,
) -> None:
    exists = conn.execute(
        "SELECT 1 FROM pg_database WHERE datname = %s", (name,)
    ).fetchone()
    if exists is not None:
        return
    if owner is None:
        conn.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
        return
    conn.execute(
        sql.SQL("CREATE DATABASE {} OWNER {}").format(
            sql.Identifier(name),
            sql.Identifier(owner),
        )
    )


def _apply_database_connect_grants(
    conn: psycopg.Connection,
    app_database: str,
    phoenix_database: str,
) -> None:
    for database in (app_database, phoenix_database):
        conn.execute(
            sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(
                sql.Identifier(database)
            )
        )
    conn.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO agentic_cataloger_app").format(
            sql.Identifier(app_database)
        )
    )
    conn.execute(
        sql.SQL("GRANT CONNECT ON DATABASE {} TO agentic_cataloger_phoenix").format(
            sql.Identifier(phoenix_database)
        )
    )


def _grant_app_schema_privileges(
    host: str, port: int, password: str, database: str
) -> None:
    app_admin = f"postgresql://postgres:{password}@{host}:{port}/{database}"
    with psycopg.connect(app_admin, autocommit=True) as conn:
        conn.execute("GRANT USAGE ON SCHEMA public TO agentic_cataloger_app")
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO agentic_cataloger_app"
        )
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT USAGE, SELECT ON SEQUENCES TO agentic_cataloger_app"
        )


def _grant_phoenix_schema_privileges(
    host: str, port: int, password: str, database: str
) -> None:
    phoenix_admin = f"postgresql://postgres:{password}@{host}:{port}/{database}"
    with psycopg.connect(phoenix_admin, autocommit=True) as conn:
        conn.execute("GRANT ALL ON SCHEMA public TO agentic_cataloger_phoenix")
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL ON TABLES TO agentic_cataloger_phoenix"
        )
        conn.execute(
            "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
            "GRANT ALL ON SEQUENCES TO agentic_cataloger_phoenix"
        )


def _docker_reachable() -> bool:
    try:
        import docker
        from docker.errors import DockerException
    except ImportError:
        return False
    try:
        docker.from_env().ping()
    except DockerException, OSError:
        return False
    return True


def _tcp_open(host: str, port: int, *, timeout_s: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def find_free_port() -> int:
    """Return an ephemeral localhost TCP port for isolated PROC tests."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def resolve_api_test_port(*, default: int = 3020) -> int:
    """Pick a port for spawned API PROC tests.

    Uses GATE-01 default **3020** when free; otherwise an ephemeral port so
    devcontainer's ambient ``api`` service does not cause false passes.
    """
    if not _tcp_open("127.0.0.1", default):
        return default
    return find_free_port()


def _resolve_external_postgres() -> PostgresHarness | None:
    """Match scripts/ci/backend-test.sh host detection; target isolated ``*_test`` DBs."""
    password = os.environ.get("PGPASSWORD", "postgres")
    kwargs = {
        "password": password,
        "app_database": APP_DB_TEST,
        "phoenix_database": PHOENIX_DB_TEST,
    }
    if host := os.environ.get("PGHOST"):
        port = int(os.environ.get("PGPORT", "5432"))
        if _tcp_open(host, port):
            return PostgresHarness(host=host, port=port, **kwargs)
        return None
    if _tcp_open("postgres", 5432):
        return PostgresHarness(host="postgres", port=5432, **kwargs)
    if _tcp_open("localhost", 3021):
        return PostgresHarness(host="localhost", port=3021, **kwargs)
    return None


@pytest.fixture(scope="session")
def postgres() -> Generator[PostgresHarness, None, None]:
    """Disposable Postgres via testcontainers, or ``*_test`` DBs when Docker is absent."""
    if _docker_reachable():
        from testcontainers.postgres import PostgresContainer

        with PostgresContainer(
            POSTGRES_IMAGE, username="postgres", password="test"
        ) as container:
            host = container.get_container_host_ip()
            port = int(container.get_exposed_port(5432))
            bootstrap_gate02_roles(host, port, password="test")
            yield PostgresHarness(host=host, port=port, password="test")
        return

    external = _resolve_external_postgres()
    if external is None:
        pytest.fail(
            "No Docker daemon and no external Postgres "
            "(set PGHOST/PGPORT, or start compose postgres / localhost:3021)"
        )
    ensure_external_test_databases(external)
    yield external


@pytest.fixture
def migrate_url(postgres: PostgresHarness) -> str:
    return postgres.migrate_url


@pytest.fixture
def app_database_url(postgres: PostgresHarness) -> str:
    return postgres.app_url


@pytest.fixture
def phoenix_database_url(postgres: PostgresHarness) -> str:
    return postgres.phoenix_url


@pytest.fixture
def migrated_database(
    migrate_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[str]:
    monkeypatch.setenv("MIGRATE_DATABASE_URL", migrate_url)
    from agentic_cataloger.platform.roles.migrate import run_migrate

    assert run_migrate() == 0
    yield migrate_url


def spawn_role(
    role: str,
    *,
    env: dict[str, str] | None = None,
) -> subprocess.Popen[str]:
    """Spawn a `agentic-cataloger <role>` process for PROC-level tests."""
    merged = os.environ.copy()
    if env:
        merged.update(env)
    # So readiness logs appear promptly when stderr is a pipe (not a TTY).
    merged.setdefault("PYTHONUNBUFFERED", "1")
    cli_bin = BACKEND_ROOT / ".venv" / "bin" / "agentic-cataloger"
    command = (
        [str(cli_bin), role]
        if cli_bin.exists()
        else [
            sys.executable,
            "-m",
            "agentic_cataloger.platform.cli",
            role,
        ]
    )
    return subprocess.Popen(
        command,
        cwd=BACKEND_ROOT,
        env=merged,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def wait_for_role_log(
    proc: subprocess.Popen[str],
    needle: str,
    *,
    timeout_s: float = 30.0,
) -> str:
    """Read ``proc.stderr`` until ``needle`` appears; return buffered text so far.

    Remaining stderr must be combined by the caller after ``communicate``:
    ``pre + (stderr or "")``.

    Raises:
        AssertionError: Process exits before the needle is seen.
        TimeoutError: Needle not seen within ``timeout_s``.
    """
    if proc.stderr is None:
        raise AssertionError("spawned role has no stderr pipe")
    deadline = time.time() + timeout_s
    buf = ""
    while time.time() < deadline:
        if needle in buf:
            return buf
        if proc.poll() is not None:
            buf += proc.stderr.read()
            raise AssertionError(
                f"role exited before log {needle!r} (rc={proc.returncode}): {buf}"
            )
        ready, _, _ = select.select([proc.stderr], [], [], 0.2)
        if not ready:
            continue
        line = proc.stderr.readline()
        if line:
            buf += line
    raise TimeoutError(f"log {needle!r} not seen within {timeout_s}s: {buf}")


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
    import urllib.request

    deadline = time.time() + timeout_s
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status < 500:
                    return
        except Exception as exc:
            last_error = exc
            time.sleep(0.2)
    raise TimeoutError(f"HTTP not ready at {url}: {last_error}")
