"""Migrate role: NFR19 one-shot bootstrap orchestrator."""

from __future__ import annotations

import asyncio
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import LiteralString, cast
from urllib.error import URLError
from urllib.request import urlopen

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agentic_cataloger.platform.errors import (
    BootstrapError,
    DatabaseNotReadyError,
    MigrateError,
)

BACKEND_ROOT = Path(__file__).resolve().parents[4]
PGQUEUER_SCHEMA = "pgqueuer"
LANGGRAPH_SCHEMA = "langgraph"
APP_ROLE = "agentic_cataloger_app"
HTTP_OK = 200
HTTP_REDIRECT = 300

logger = logging.getLogger(__name__)


def run_migrate() -> int:
    """Run NFR19 bootstrap and return a process exit code.

    Returns:
        ``0`` on success, ``1`` on configuration or bootstrap failure.
    """
    migrate_url = os.environ.get("MIGRATE_DATABASE_URL", "").strip()
    if not migrate_url:
        logger.error("MIGRATE_DATABASE_URL is required for migrate role")
        return 1

    try:
        _wait_for_database(migrate_url)
        _verify_databases_exist(migrate_url)
        _run_alembic_upgrade(migrate_url)
        _install_pgqueuer(migrate_url)
        _install_langgraph(migrate_url)
        _grant_vendor_schema_privileges(migrate_url)
        _wait_for_phoenix_database()
        _wait_for_phoenix_http()
        _verify_bootstrap_state(migrate_url)
    except MigrateError:
        logger.exception("migrate failed")
        return 1

    logger.info("migrate completed successfully")
    return 0


def _wait_for_database(
    url: str,
    *,
    attempts: int = 30,
    delay_s: float = 1.0,
    label: str = "database",
) -> None:
    """Poll Postgres until ``SELECT 1`` succeeds or attempts are exhausted.

    Args:
        url: Postgres connection URL.
        attempts: Maximum connection attempts.
        delay_s: Sleep between failed attempts, in seconds.
        label: Name used in the timeout error message.

    Raises:
        DatabaseNotReadyError: If the database never becomes reachable.
    """
    last_error: BaseException | None = None
    for _ in range(attempts):
        try:
            with psycopg.connect(url, autocommit=True) as conn:
                conn.execute("SELECT 1")
        except (psycopg.Error, OSError) as exc:
            last_error = exc
            time.sleep(delay_s)
        else:
            return
    raise DatabaseNotReadyError(f"{label} not ready: {last_error}")


def _verify_databases_exist(migrate_url: str) -> None:
    """Fail when ``agentic_cataloger_app`` or ``agentic_cataloger_phoenix`` is missing.

    Args:
        migrate_url: Superuser connection URL used for catalog queries.

    Raises:
        BootstrapError: If either required database is absent.
    """
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT datname FROM pg_database "
            "WHERE datname IN ('agentic_cataloger_app', 'agentic_cataloger_phoenix')"
        ).fetchall()
    names = {row[0] for row in rows}
    missing = {"agentic_cataloger_app", "agentic_cataloger_phoenix"} - names
    if missing:
        raise BootstrapError(f"missing databases after init: {sorted(missing)}")


def _run_alembic_upgrade(migrate_url: str) -> None:
    """Run ``alembic upgrade head`` against the migrate database.

    Args:
        migrate_url: Value exported as ``MIGRATE_DATABASE_URL`` for Alembic.

    Raises:
        BootstrapError: If the Alembic subprocess exits non-zero.
    """
    env = os.environ.copy()
    env["MIGRATE_DATABASE_URL"] = migrate_url
    result = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=BACKEND_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        detail = result.stderr or result.stdout
        raise BootstrapError(f"alembic upgrade failed ({result.returncode}): {detail}")


def _install_pgqueuer(migrate_url: str) -> None:
    """Install or upgrade the PgQueuer schema (sync wrapper).

    Args:
        migrate_url: Superuser connection URL for schema setup.
    """
    asyncio.run(_install_pgqueuer_async(migrate_url))


async def _install_pgqueuer_async(migrate_url: str) -> None:
    """Install or upgrade PgQueuer tables under ``PGQUEUER_SCHEMA``.

    Args:
        migrate_url: Superuser connection URL for schema setup.
    """
    import psycopg
    from pgqueuer.adapters.drivers.psycopg import PsycopgDriver
    from pgqueuer.adapters.persistence import qb
    from pgqueuer.domain.settings import DBSettings
    from pgqueuer.queries import Queries

    settings = DBSettings(db_schema=PGQUEUER_SCHEMA)
    qbe = qb.QueryBuilderEnvironment(settings=settings)

    async with await psycopg.AsyncConnection.connect(
        migrate_url, autocommit=True
    ) as conn:
        queries = Queries(PsycopgDriver(conn), qbe=qbe)
        if not await queries.has_table(settings.queue_table):
            await queries.install()
        await queries.upgrade()


def _langgraph_conn_string(base_url: str) -> str:
    """Build a LangGraph checkpointer URL with ``search_path`` set.

    Args:
        base_url: Base Postgres URL (may already include query params).

    Returns:
        Connection string forcing ``search_path`` to ``LANGGRAPH_SCHEMA``.
    """
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}options=-c%20search_path%3D{LANGGRAPH_SCHEMA}"


async def _install_langgraph_async(migrate_url: str) -> None:
    """Create the LangGraph schema and run AsyncPostgresSaver setup.

    Args:
        migrate_url: Superuser connection URL for schema setup.
    """
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {LANGGRAPH_SCHEMA}")

    conn_string = _langgraph_conn_string(migrate_url)
    async with AsyncPostgresSaver.from_conn_string(conn_string) as saver:
        await saver.setup()


def _install_langgraph(migrate_url: str) -> None:
    """Install LangGraph checkpoint schema (sync wrapper).

    Args:
        migrate_url: Superuser connection URL for schema setup.
    """
    asyncio.run(_install_langgraph_async(migrate_url))


def _grant_vendor_schema_privileges(migrate_url: str) -> None:
    """Grant app-role DML on vendor schemas; revoke CREATE.

    Args:
        migrate_url: Superuser connection URL used to apply GRANTs.
    """
    statements = [
        f"GRANT USAGE ON SCHEMA {PGQUEUER_SCHEMA} TO {APP_ROLE}",
        (
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
            f"IN SCHEMA {PGQUEUER_SCHEMA} TO {APP_ROLE}"
        ),
        (
            f"GRANT USAGE, SELECT ON ALL SEQUENCES "
            f"IN SCHEMA {PGQUEUER_SCHEMA} TO {APP_ROLE}"
        ),
        f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {PGQUEUER_SCHEMA} TO {APP_ROLE}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {PGQUEUER_SCHEMA} "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {PGQUEUER_SCHEMA} "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}",
        f"GRANT USAGE ON SCHEMA {LANGGRAPH_SCHEMA} TO {APP_ROLE}",
        (
            f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES "
            f"IN SCHEMA {LANGGRAPH_SCHEMA} TO {APP_ROLE}"
        ),
        (
            f"GRANT USAGE, SELECT ON ALL SEQUENCES "
            f"IN SCHEMA {LANGGRAPH_SCHEMA} TO {APP_ROLE}"
        ),
        f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {LANGGRAPH_SCHEMA} TO {APP_ROLE}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {LANGGRAPH_SCHEMA} "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {LANGGRAPH_SCHEMA} "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}",
        f"REVOKE CREATE ON SCHEMA {PGQUEUER_SCHEMA} FROM {APP_ROLE}",
        f"REVOKE CREATE ON SCHEMA {LANGGRAPH_SCHEMA} FROM {APP_ROLE}",
    ]
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        for statement in statements:
            # Dynamic DDL strings are not LiteralString; cast for psycopg typing.
            conn.execute(cast(LiteralString, statement))


def _phoenix_database_url() -> str | None:
    """Return ``PHOENIX_DATABASE_URL`` when set.

    Returns:
        Connection URL, or ``None`` when Phoenix DB wait should be skipped.
    """
    return os.environ.get("PHOENIX_DATABASE_URL")


def _wait_for_phoenix_database(*, attempts: int = 30, delay_s: float = 2.0) -> None:
    """Wait for Phoenix DB when ``PHOENIX_DATABASE_URL`` is set.

    Args:
        attempts: Maximum connection attempts.
        delay_s: Sleep between failed attempts, in seconds.
    """
    url = _phoenix_database_url()
    if not url:
        return
    _wait_for_database(
        url, attempts=attempts, delay_s=delay_s, label="phoenix database"
    )


def _wait_for_phoenix_http(*, attempts: int = 30, delay_s: float = 2.0) -> None:
    """Wait for Phoenix HTTP when ``PHOENIX_HOST`` is set. Skipped in CI.

    Args:
        attempts: Maximum HTTP probes.
        delay_s: Sleep between failed probes, in seconds.

    Raises:
        DatabaseNotReadyError: If the HTTP endpoint never returns a success status.
    """
    host = os.environ.get("PHOENIX_HOST")
    if not host:
        return
    port = os.environ.get("PHOENIX_PORT", "6006")
    endpoint = f"http://{host}:{port}/"
    last_error: BaseException | None = None
    for _ in range(attempts):
        try:
            with urlopen(endpoint, timeout=3) as response:
                if HTTP_OK <= response.status < HTTP_REDIRECT:
                    return
        except (URLError, TimeoutError, OSError) as exc:
            last_error = exc
        time.sleep(delay_s)
    raise DatabaseNotReadyError(f"phoenix HTTP not ready at {endpoint}: {last_error}")


def _verify_bootstrap_state(migrate_url: str) -> None:
    """Assert Alembic version and vendor schemas exist after migrate.

    Args:
        migrate_url: Connection URL used for post-bootstrap checks.

    Raises:
        BootstrapError: If alembic_version or a vendor schema is missing.
    """
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        version = conn.execute(
            "SELECT version_num FROM public.alembic_version"
        ).fetchone()
        if not version:
            raise BootstrapError("alembic_version missing after migrate")
        for schema in (PGQUEUER_SCHEMA, LANGGRAPH_SCHEMA):
            exists = conn.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema,),
            ).fetchone()
            if not exists:
                raise BootstrapError(f"schema {schema} missing after migrate")
