"""Bootstrap order and idempotence integration tests (1.2-INT-001/002)."""

from __future__ import annotations

import psycopg
import pytest


@pytest.mark.integration
def test_int_001_bootstrap_creates_vendor_schemas(migrated_database: str) -> None:
    with psycopg.connect(migrated_database, autocommit=True) as conn:
        version = conn.execute("SELECT version_num FROM public.alembic_version").fetchone()
        assert version is not None
        for schema in ("pgqueuer", "langgraph"):
            row = conn.execute(
                "SELECT 1 FROM information_schema.schemata WHERE schema_name = %s",
                (schema,),
            ).fetchone()
            assert row is not None, f"missing schema {schema}"


@pytest.mark.integration
def test_int_002_migrate_is_idempotent(migrate_url: str, monkeypatch: pytest.MonkeyPatch) -> None:
    from pricecomp.platform.roles.migrate import run_migrate

    monkeypatch.setenv("MIGRATE_DATABASE_URL", migrate_url)
    assert run_migrate() == 0
    assert run_migrate() == 0
