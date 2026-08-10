"""Psycopg persistence adapter for review's deferred_items table."""

from __future__ import annotations

from typing import Any, final
from uuid import UUID

import psycopg
from psycopg.types.json import Jsonb

from agentic_cataloger.contracts.models import StageKind
from agentic_cataloger.platform.persistence.catalog_repo import (
    PsycopgUnitOfWork,
    connect_app,
)
from agentic_cataloger.review.models import DeferredItem, DeferredItemStatus, ReasonCode
from agentic_cataloger.review.ports import DeferredItemRepository, ReviewUnitOfWork

# Re-export shared connection / UoW helpers used by the review runner.
__all__ = [
    "PsycopgDeferredItemRepository",
    "PsycopgUnitOfWork",
    "ReviewUnitOfWork",
    "connect_app",
]


@final
class PsycopgDeferredItemRepository(DeferredItemRepository):
    """Deferred-item repository backed by ``deferred_items``."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        """Create a repository on an exclusively leased ``conn``.

        Args:
            conn: Live psycopg connection. Not safe to share across threads
                or parallel tool calls.
        """
        super().__init__()
        self._conn = conn

    def add(self, item: DeferredItem) -> DeferredItem:
        """Insert a new deferred item row.

        Args:
            item: Deferred item to persist.

        Returns:
            The same item instance after insert.
        """
        self._conn.execute(
            """
            INSERT INTO deferred_items (
                id, product_id, stage, reason_code, attempt_count,
                payload_snapshot, evidence_span, trace_id, status
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                item.id,
                item.product_id,
                item.stage,
                item.reason_code,
                item.attempt_count,
                Jsonb(dict(item.payload_snapshot)),
                item.evidence_span,
                item.trace_id,
                item.status,
            ),
        )
        return item

    def list_open(self) -> list[DeferredItem]:
        """Return every deferred item with ``status = 'open'``."""
        rows = self._conn.execute(
            """
            SELECT id, product_id, stage, reason_code, attempt_count,
                   payload_snapshot, evidence_span, trace_id, status, created_at
            FROM deferred_items
            WHERE status = 'open'
            ORDER BY created_at, id
            """
        ).fetchall()
        return [_deferred_item_from_row(row) for row in rows]


def _deferred_item_from_row(row: Any) -> DeferredItem:
    data = _as_mapping(row)
    return DeferredItem(
        id=UUID(str(data["id"])),
        product_id=UUID(str(data["product_id"])),
        stage=StageKind(data["stage"]),
        reason_code=ReasonCode(data["reason_code"]),
        attempt_count=int(data["attempt_count"]),
        payload_snapshot=dict(data["payload_snapshot"]),
        evidence_span=_optional_str(data.get("evidence_span")),
        trace_id=_optional_str(data.get("trace_id")),
        status=DeferredItemStatus(data["status"]),
        created_at=data.get("created_at"),
    )


def _as_mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    msg = f"Expected dict row, got {type(row)!r}"
    raise TypeError(msg)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
