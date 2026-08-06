"""Select the products a pipeline run operates on."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.pipeline.models import SelectRunProductsResult
from agentic_cataloger.pipeline.ports import RunProductRepository


@dataclass(frozen=True, slots=True)
class SelectRunProductsRequest:
    """Inputs for selecting the products a pipeline run will operate on."""

    ingest_filter: IngestFilter
    unassigned_only: bool = True
    limit: int | None = None


def select_run_products(
    request: SelectRunProductsRequest,
    *,
    products: RunProductRepository,
) -> SelectRunProductsResult:
    """Select the products a pipeline run will operate on.

    Pure pass-through to the port — the filter semantics live in the SQL
    (mirroring ``IngestFilter.matches``), this just shapes the request/result
    the way every other command file does.

    Args:
        request: Filter, unassigned-only flag, and optional row cap.
        products: Product-selection repository.

    Returns:
        Matching products.
    """
    matched = products.list_for_run(
        ingest_filter=request.ingest_filter,
        unassigned_only=request.unassigned_only,
        limit=request.limit,
    )
    return SelectRunProductsResult(products=tuple(matched))


__all__ = ["SelectRunProductsRequest", "select_run_products"]
