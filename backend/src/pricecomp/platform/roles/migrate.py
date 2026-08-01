"""Migrate role: NFR19 one-shot bootstrap orchestrator."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

import psycopg
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

BACKEND_ROOT = Path(__file__).resolve().parents[4]
PGQUEUER_SCHEMA = "pgqueuer"
LANGGRAPH_SCHEMA = "langgraph"
APP_ROLE = "pricecomp_app"


def run_migrate() -> int:
    migrate_url = os.environ.get("MIGRATE_DATABASE_URL")
    if not migrate_url:
        print("MIGRATE_DATABASE_URL is required for migrate role", file=sys.stderr)
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
    except Exception as exc:  # noqa: BLE001 — migrate must exit non-zero on failure
        print(f"migrate failed: {exc}", file=sys.stderr)
        return 1

    print("migrate completed successfully")
    return 0


def _wait_for_database(url: str, *, attempts: int = 30, delay_s: float = 1.0) -> None:
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with psycopg.connect(url, autocommit=True) as conn:
                conn.execute("SELECT 1")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(delay_s)
    raise RuntimeError(f"database not ready: {last_error}")


def _verify_databases_exist(migrate_url: str) -> None:
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        rows = conn.execute(
            "SELECT datname FROM pg_database WHERE datname IN ('pricecomp_app', 'pricecomp_phoenix')"
        ).fetchall()
    names = {row[0] for row in rows}
    missing = {"pricecomp_app", "pricecomp_phoenix"} - names
    if missing:
        raise RuntimeError(f"missing databases after init: {sorted(missing)}")


def _run_alembic_upgrade(migrate_url: str) -> None:
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
        raise RuntimeError(
            f"alembic upgrade failed ({result.returncode}): {result.stderr or result.stdout}"
        )


def _install_pgqueuer(migrate_url: str) -> None:
    asyncio.run(_install_pgqueuer_async(migrate_url))


async def _install_pgqueuer_async(migrate_url: str) -> None:
    import psycopg
    from pgqueuer.adapters.drivers.psycopg import PsycopgDriver
    from pgqueuer.adapters.persistence import qb
    from pgqueuer.domain.settings import DBSettings
    from pgqueuer.queries import Queries

    settings = DBSettings(db_schema=PGQUEUER_SCHEMA)
    qbe = qb.QueryBuilderEnvironment(settings=settings)

    async with await psycopg.AsyncConnection.connect(migrate_url, autocommit=True) as conn:
        queries = Queries(PsycopgDriver(conn), qbe=qbe)
        if not await queries.has_table(settings.queue_table):
            await queries.install()
        await queries.upgrade()


def _langgraph_conn_string(base_url: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}options=-c%20search_path%3D{LANGGRAPH_SCHEMA}"


async def _install_langgraph_async(migrate_url: str) -> None:
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {LANGGRAPH_SCHEMA}")

    conn_string = _langgraph_conn_string(migrate_url)
    async with AsyncPostgresSaver.from_conn_string(conn_string) as saver:
        await saver.setup()


def _install_langgraph(migrate_url: str) -> None:
    asyncio.run(_install_langgraph_async(migrate_url))


def _grant_vendor_schema_privileges(migrate_url: str) -> None:
    statements = [
        f"GRANT USAGE ON SCHEMA {PGQUEUER_SCHEMA} TO {APP_ROLE}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {PGQUEUER_SCHEMA} TO {APP_ROLE}",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {PGQUEUER_SCHEMA} TO {APP_ROLE}",
        f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA {PGQUEUER_SCHEMA} TO {APP_ROLE}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {PGQUEUER_SCHEMA} "
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO {APP_ROLE}",
        f"ALTER DEFAULT PRIVILEGES IN SCHEMA {PGQUEUER_SCHEMA} "
        f"GRANT USAGE, SELECT ON SEQUENCES TO {APP_ROLE}",
        f"GRANT USAGE ON SCHEMA {LANGGRAPH_SCHEMA} TO {APP_ROLE}",
        f"GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA {LANGGRAPH_SCHEMA} TO {APP_ROLE}",
        f"GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA {LANGGRAPH_SCHEMA} TO {APP_ROLE}",
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
            conn.execute(statement)


def _phoenix_database_url() -> str | None:
    return os.environ.get("PHOENIX_DATABASE_URL")


def _wait_for_phoenix_database(*, attempts: int = 30, delay_s: float = 2.0) -> None:
    url = _phoenix_database_url()
    if not url:
        return
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with psycopg.connect(url, autocommit=True) as conn:
                conn.execute("SELECT 1")
            return
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            time.sleep(delay_s)
    raise RuntimeError(f"phoenix database not ready: {last_error}")


def _wait_for_phoenix_http(*, attempts: int = 30, delay_s: float = 2.0) -> None:
    host = os.environ.get("PHOENIX_HOST")
    if not host:
        return
    port = os.environ.get("PHOENIX_PORT", "6006")
    endpoint = f"http://{host}:{port}/"
    last_error: Exception | None = None
    for _ in range(attempts):
        try:
            with urlopen(endpoint, timeout=3) as response:  # noqa: S310
                if response.status < 500:
                    return
        except URLError as exc:
            last_error = exc
        except Exception as exc:  # noqa: BLE001
            last_error = exc
        time.sleep(delay_s)
    raise RuntimeError(f"phoenix HTTP not ready at {endpoint}: {last_error}")


def _verify_bootstrap_state(migrate_url: str) -> None:
    with psycopg.connect(migrate_url, autocommit=True) as conn:
        version = conn.execute(
            "SELECT version_num FROM public.alembic_version"
        ).fetchone()
        if not version:
            raise RuntimeError("alembic_version missing after migrate")
        for schema in (PGQUEUER_SCHEMA, LANGGRAPH_SCHEMA):
            exists = conn.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema,),
            ).fetchone()
            if not exists:
                raise RuntimeError(f"schema {schema} missing after migrate")
