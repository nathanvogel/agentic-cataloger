"""Wire DB adapters to pipeline application commands."""

from __future__ import annotations

import logging
import os

from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.pipeline.commands import (
    SelectRunProductsRequest,
    select_run_products,
)
from agentic_cataloger.pipeline.models import SelectRunProductsResult
from agentic_cataloger.platform.persistence.catalog_repo import connect_app
from agentic_cataloger.platform.persistence.pipeline_repo import (
    PsycopgRunProductRepository,
)

logger = logging.getLogger(__name__)


def _require_database_url(database_url: str | None) -> str:
    url = (database_url or os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        msg = "DATABASE_URL must be set for pipeline commands"
        raise RuntimeError(msg)
    return url


def run_select_products(
    *,
    ingest_filter: IngestFilter,
    limit: int | None = None,
    unassigned_only: bool = True,
    database_url: str | None = None,
) -> SelectRunProductsResult:
    """Select the products a pipeline run would operate on (read-only).

    Args:
        ingest_filter: Category/keyword criteria (empty = every product).
        limit: Optional row cap; None means no limit.
        unassigned_only: Exclude products with an existing taxonomy leaf
            membership when True (the default — re-running after a prompt
            fix shouldn't re-pay for finished products). Pass False for
            ``--reassign``.
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Matching products.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        return select_run_products(
            SelectRunProductsRequest(
                ingest_filter=ingest_filter,
                unassigned_only=unassigned_only,
                limit=limit,
            ),
            products=PsycopgRunProductRepository(conn),
        )


__all__ = ["run_select_products"]
