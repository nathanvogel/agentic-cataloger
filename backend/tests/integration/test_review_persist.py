"""Integration tests for review's deferred_items persistence."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest

from agentic_cataloger.catalog.commands import ImportSnapshotRequest, import_snapshot
from agentic_cataloger.catalog.identity import SourceIdentity
from agentic_cataloger.catalog.models import ProductObservation
from agentic_cataloger.contracts.models import StageKind
from agentic_cataloger.platform.persistence.catalog_repo import (
    PsycopgProductRepository,
    PsycopgSnapshotRepository,
    PsycopgUnitOfWork,
    connect_app,
)
from agentic_cataloger.platform.persistence.review_repo import (
    PsycopgDeferredItemRepository,
)
from agentic_cataloger.platform.review.runner import (
    run_defer_item,
    run_list_deferred_items,
)
from agentic_cataloger.review.commands import DeferItemRequest, defer_item
from agentic_cataloger.review.models import ReasonCode


def _seed_product(conn: psycopg.Connection[Any], *, product_id: str = "700") -> UUID:
    """Insert one catalog product via import_snapshot; return its app id."""
    result = import_snapshot(
        ImportSnapshotRequest(
            source_namespace="migros-ch",
            source_observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            content_checksum=f"review-{product_id}-{uuid4()}",
            source_path="test.csv",
            observations=[
                ProductObservation(
                    identity=SourceIdentity("migros-ch", product_id),
                    name="Test milk",
                    product_url=f"https://www.migros.ch/de/product/{product_id}",
                    shelf_price=Decimal("1.50"),
                )
            ],
            deferred=[],
        ),
        snapshots=PsycopgSnapshotRepository(conn),
        products=PsycopgProductRepository(conn),
        uow=PsycopgUnitOfWork(conn),
    )
    product = PsycopgProductRepository(conn).get_by_source_identity(
        SourceIdentity("migros-ch", product_id)
    )
    assert product is not None
    assert result.upserted_count == 1
    return product.id


def _clear_deferred_items(conn: psycopg.Connection[Any]) -> None:
    conn.execute("DELETE FROM deferred_items")
    conn.commit()


@pytest.mark.integration
def test_defer_then_list_round_trips_payload(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """A deferred item round-trips through the CLI runner, JSONB payload intact."""
    with connect_app(app_database_url) as conn:
        _clear_deferred_items(conn)
        product_id = _seed_product(conn)

    payload = {"note": "no trustworthy candidate", "score": 0.42}
    deferred = run_defer_item(
        DeferItemRequest(
            product_id=product_id,
            stage=StageKind.ASSIGN,
            reason_code=ReasonCode.LOW_CONFIDENCE,
            attempt_count=2,
            payload_snapshot=payload,
            evidence_span="p.42 'unclear category'",
            trace_id="trace-abc",
        ),
        database_url=app_database_url,
    ).item

    assert deferred.product_id == product_id
    assert deferred.payload_snapshot == payload

    result = run_list_deferred_items(database_url=app_database_url)

    assert len(result.items) == 1
    item = result.items[0]
    assert item.id == deferred.id
    assert item.product_id == product_id
    assert item.stage == StageKind.ASSIGN
    assert item.reason_code == ReasonCode.LOW_CONFIDENCE
    assert item.attempt_count == 2
    assert item.payload_snapshot == payload
    assert item.evidence_span == "p.42 'unclear category'"
    assert item.trace_id == "trace-abc"
    assert item.status.value == "open"
    assert item.created_at is not None


@pytest.mark.integration
def test_list_open_returns_only_open_rows(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """list_open filters on status='open'; the CHECK constraint forbids any other
    value today (no re-drive/resolution status exists until 5.1), so this also
    proves no non-'open' row can slip past the filter.
    """
    with connect_app(app_database_url) as conn:
        _clear_deferred_items(conn)
        product_id = _seed_product(conn, product_id="701")

        item = defer_item(
            DeferItemRequest(
                product_id=product_id,
                stage=StageKind.DISCOVER_CREATE,
                reason_code=ReasonCode.UNKNOWN,
                attempt_count=1,
                payload_snapshot={"note": "still open"},
            ),
            items=PsycopgDeferredItemRepository(conn),
            uow=PsycopgUnitOfWork(conn),
        ).item

        open_items = PsycopgDeferredItemRepository(conn).list_open()
        assert [row.id for row in open_items] == [item.id]

        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                "UPDATE deferred_items SET status = 'closed' WHERE id = %s",
                (item.id,),
            )
        conn.rollback()


@pytest.mark.integration
def test_defer_item_rejects_unknown_product_fk(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Deferring against a non-existent product_id raises the FK violation."""
    with connect_app(app_database_url) as conn:
        _clear_deferred_items(conn)
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            defer_item(
                DeferItemRequest(
                    product_id=uuid4(),
                    stage=StageKind.ASSIGN,
                    reason_code=ReasonCode.DEFER,
                    attempt_count=1,
                    payload_snapshot={},
                ),
                items=PsycopgDeferredItemRepository(conn),
                uow=PsycopgUnitOfWork(conn),
            )
        conn.rollback()


@pytest.mark.integration
def test_defer_item_rejects_bad_stage_and_reason_code_at_db(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """A raw INSERT with a bad stage/reason_code value hits the CHECK constraint."""
    with connect_app(app_database_url) as conn:
        _clear_deferred_items(conn)
        product_id = _seed_product(conn, product_id="702")

        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                """
                INSERT INTO deferred_items (
                    id, product_id, stage, reason_code, attempt_count,
                    payload_snapshot
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (uuid4(), product_id, "not_a_stage", "unknown", 1, "{}"),
            )
            conn.commit()
        conn.rollback()

        with pytest.raises(psycopg.errors.CheckViolation):
            conn.execute(
                """
                INSERT INTO deferred_items (
                    id, product_id, stage, reason_code, attempt_count,
                    payload_snapshot
                ) VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (uuid4(), product_id, "assign", "not_a_reason", 1, "{}"),
            )
            conn.commit()
        conn.rollback()
