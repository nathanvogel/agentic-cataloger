"""GATE-02 privilege integration tests (1.2-INT-003/004/008/009)."""

from __future__ import annotations

import psycopg
import pytest
from testcontainers.postgres import PostgresContainer
from tests.conftest import BACKEND_ROOT, REPO_ROOT


@pytest.mark.integration
def test_int_003_app_role_cannot_create_database(app_database_url: str) -> None:
    """App role lacks CREATEDB — CREATE DATABASE must fail."""
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        with psycopg.connect(app_database_url, autocommit=True) as conn:
            conn.execute("CREATE DATABASE should_fail")


@pytest.mark.integration
def test_int_004_app_role_cannot_access_phoenix_db(
    postgres_container: PostgresContainer,
) -> None:
    """App role cannot connect to the Phoenix database."""
    port = int(postgres_container.get_exposed_port(5432))
    app_on_phoenix_db = f"postgresql://pricecomp_app:pricecomp_app_dev@localhost:{port}/pricecomp_phoenix"
    with pytest.raises(psycopg.Error):
        with psycopg.connect(app_on_phoenix_db, connect_timeout=3) as conn:
            conn.execute("SELECT 1")


@pytest.mark.integration
def test_int_008_app_role_cannot_ddl_vendor_schemas(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """App role cannot CREATE TABLE in vendor schemas (pgqueuer, langgraph)."""
    with psycopg.connect(app_database_url, autocommit=True) as conn:
        for schema in ("pgqueuer", "langgraph"):
            with pytest.raises(psycopg.Error):
                conn.execute(f"CREATE TABLE {schema}.forbidden (id int)")


@pytest.mark.integration
def test_int_009_migrate_credentials_absent_from_api_worker_env(
    app_database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MIGRATE_DATABASE_URL is absent from api/worker source and compose blocks."""
    monkeypatch.delenv("MIGRATE_DATABASE_URL", raising=False)
    monkeypatch.setenv("DATABASE_URL", app_database_url)
    api_source = (
        BACKEND_ROOT / "src" / "pricecomp" / "platform" / "roles" / "api.py"
    ).read_text()
    worker_source = (
        BACKEND_ROOT / "src" / "pricecomp" / "platform" / "roles" / "worker.py"
    ).read_text()
    compose = (REPO_ROOT / "docker-compose.yml").read_text()
    assert "MIGRATE_DATABASE_URL" not in api_source
    assert "MIGRATE_DATABASE_URL" not in worker_source
    api_block = compose.split("api:")[1].split("worker:")[0]
    worker_block = compose.split("worker:")[1]
    assert "MIGRATE_DATABASE_URL" not in api_block
    assert "MIGRATE_DATABASE_URL" not in worker_block
