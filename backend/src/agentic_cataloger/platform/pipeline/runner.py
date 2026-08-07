"""Wire DB adapters to pipeline application commands."""

from __future__ import annotations

import logging
import os
from uuid import uuid7

from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.contracts.models import StageResult
from agentic_cataloger.pipeline.commands import (
    SelectRunProductsRequest,
    select_run_products,
)
from agentic_cataloger.pipeline.models import RunSummary, SelectRunProductsResult
from agentic_cataloger.platform.persistence.catalog_repo import connect_app
from agentic_cataloger.platform.persistence.pipeline_repo import (
    PsycopgRunProductRepository,
)
from agentic_cataloger.platform.pipeline.agent import build_assign_stage_agent
from agentic_cataloger.platform.pipeline.graph import build_stage_graph
from agentic_cataloger.platform.pipeline.nodes import StageDeps
from agentic_cataloger.platform.telemetry import configure_telemetry

logger = logging.getLogger(__name__)

# Outer per-product graph: assign -> (defer) -> END is at most 2 hops in
# Phase 2 (3 once Phase 3 adds discover_create's re-entry into assign) — a
# generous ceiling that only fires on an actual orchestration bug, not on
# a slow or looping model (the agent's own recursion_limit in agent.py
# handles that).
OUTER_RECURSION_LIMIT = 10


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


def run_pipeline(
    *,
    ingest_filter: IngestFilter,
    limit: int | None = None,
    unassigned_only: bool = True,
    database_url: str | None = None,
) -> RunSummary:
    """Select products, then run the two-stage graph over each, sequentially.

    One connection per product (opened and closed around that product's
    stages, not held for the whole run) so the graph's tools all reuse the
    same live connection without an idle-in-transaction connection held
    across the entire run's LLM latency. Sequential by design: product N's
    stages need to see what product N-1's discover stage created — no
    concurrency here (roadmap 4.5's "launched from an ingest filter", not
    "run in parallel").

    Args:
        ingest_filter: Category/keyword criteria (empty = every product).
        limit: Optional row cap; None means no limit.
        unassigned_only: Exclude products with an existing taxonomy leaf
            membership when True (the default). Pass False for
            ``--reassign``.
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Counts for the CLI summary line. ``created_count``/
        ``disagreement_count`` stay 0 until Phase 3 adds discover/create.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        selected = select_run_products(
            SelectRunProductsRequest(
                ingest_filter=ingest_filter,
                unassigned_only=unassigned_only,
                limit=limit,
            ),
            products=PsycopgRunProductRepository(conn),
        )

    telemetry = configure_telemetry()
    graph = build_stage_graph()
    deferred_count = 0
    for product in selected.products:
        run_id = uuid7()
        with connect_app(url) as conn:
            stage_agent = build_assign_stage_agent(conn)
            outcome = graph.invoke(
                {
                    "product": product,
                    "run_id": str(run_id),
                    "discover_ran": False,
                },
                config={"run_id": run_id, "recursion_limit": OUTER_RECURSION_LIMIT},
                context=StageDeps(
                    conn=conn, telemetry=telemetry, stage_agent=stage_agent
                ),
            )
        result: StageResult = outcome["assign"]
        if result.status != "success":
            deferred_count += 1
        logger.info(
            "pipeline product_id=%s run_id=%s status=%s",
            product.product_id,
            run_id,
            result.status,
        )

    return RunSummary(
        product_count=len(selected.products),
        deferred_count=deferred_count,
    )


__all__ = ["run_pipeline", "run_select_products"]
