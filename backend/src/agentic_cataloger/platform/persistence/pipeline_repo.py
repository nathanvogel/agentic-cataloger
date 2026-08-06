"""Psycopg persistence adapter for pipeline product selection."""

from __future__ import annotations

from typing import Any, final
from uuid import UUID

import psycopg
from psycopg import sql

from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.pipeline.models import RunProductRef
from agentic_cataloger.pipeline.ports import RunProductRepository


@final
class PsycopgRunProductRepository(RunProductRepository):
    """Select a set of catalog products for a pipeline run.

    Mirrors ``IngestFilter.matches`` in SQL: ``source_category`` matches as a
    case-insensitive substring of the retailer ``source_category`` OR an
    exact case-insensitive match of ``unified_category``; ``keyword``
    matches as a case-insensitive substring of ``name`` or ``name_de``. Both
    AND together when both are set. No index on these columns yet — a known
    cliff at MVP scale, not an oversight.
    """

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        """Create a repository on ``conn``.

        Args:
            conn: Live psycopg connection.
        """
        super().__init__()
        self._conn = conn

    def list_for_run(
        self,
        *,
        ingest_filter: IngestFilter,
        unassigned_only: bool,
        limit: int | None,
    ) -> list[RunProductRef]:
        """Return catalog products matching ``ingest_filter``.

        Args:
            ingest_filter: Category/keyword criteria (empty = no filtering).
            unassigned_only: Exclude products with an existing taxonomy leaf
                membership when True.
            limit: Optional row cap; None means no limit.

        Returns:
            Matching products, ordered by name (then id) for a stable run
            order.
        """
        # Each fragment below is a string literal, not a runtime-built value —
        # sql.SQL() intentionally rejects non-literal strings (it does no
        # escaping). Dynamic parts only ever reach the query as %()s bind
        # parameters in `params`, never spliced into the SQL text itself.
        conditions: list[sql.Composable] = []
        params: dict[str, object] = {}

        if ingest_filter.source_category is not None:
            conditions.append(
                sql.SQL(
                    "(source_category ILIKE %(source_category_needle)s "
                    "OR lower(unified_category) = lower(%(source_category)s))"
                )
            )
            params["source_category_needle"] = f"%{ingest_filter.source_category}%"
            params["source_category"] = ingest_filter.source_category

        if ingest_filter.keyword is not None:
            conditions.append(
                sql.SQL(
                    "(name ILIKE %(keyword_needle)s "
                    "OR name_de ILIKE %(keyword_needle)s)"
                )
            )
            params["keyword_needle"] = f"%{ingest_filter.keyword}%"

        if unassigned_only:
            conditions.append(
                sql.SQL(
                    "NOT EXISTS ("
                    "SELECT 1 FROM taxonomy_memberships m "
                    "WHERE m.product_id = catalog_products.id"
                    ")"
                )
            )

        query_parts: list[sql.Composable] = [
            sql.SQL(
                "SELECT id, name, name_de, source_category, unified_category "
                "FROM catalog_products"
            )
        ]
        if conditions:
            query_parts.append(sql.SQL(" WHERE "))
            query_parts.append(sql.SQL(" AND ").join(conditions))
        query_parts.append(sql.SQL(" ORDER BY name, id"))
        if limit is not None:
            query_parts.append(sql.SQL(" LIMIT %(limit)s"))
            params["limit"] = limit

        query = sql.SQL("").join(query_parts)
        rows = self._conn.execute(query, params).fetchall()
        return [_run_product_ref_from_row(row) for row in rows]


def _run_product_ref_from_row(row: Any) -> RunProductRef:
    data = _as_mapping(row)
    return RunProductRef(
        product_id=UUID(str(data["id"])),
        name=str(data["name"]),
        name_de=_optional_str(data.get("name_de")),
        source_category=_optional_str(data.get("source_category")),
        unified_category=_optional_str(data.get("unified_category")),
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


__all__ = ["PsycopgRunProductRepository"]
