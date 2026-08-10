"""Wire DB adapters to pipeline application commands."""

from __future__ import annotations

import logging
import os
from typing import Any, Final
from uuid import UUID, uuid7

from phoenix.otel import OpenInferenceSpanKindValues, SpanAttributes

from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.contracts.models import StageResult
from agentic_cataloger.pipeline.commands import (
    SelectRunProductsRequest,
    ensure_root_category,
    select_run_products,
)
from agentic_cataloger.pipeline.models import (
    AssignDecision,
    RunProductRef,
    RunSummary,
    SelectRunProductsResult,
)
from agentic_cataloger.pipeline.ports import Telemetry
from agentic_cataloger.platform.persistence.catalog_repo import connect_app
from agentic_cataloger.platform.persistence.pipeline_repo import (
    PsycopgRunProductRepository,
)
from agentic_cataloger.platform.persistence.taxonomy_repo import (
    PsycopgCategoryRepository,
    PsycopgMembershipRepository,
    PsycopgUnitOfWork,
)
from agentic_cataloger.platform.pipeline.agent import (
    build_assign_stage_agent,
    build_discover_stage_agent,
)
from agentic_cataloger.platform.pipeline.graph import build_stage_graph
from agentic_cataloger.platform.pipeline.nodes import StageDeps
from agentic_cataloger.platform.telemetry import configure_telemetry

logger = logging.getLogger(__name__)

# Outer per-product graph: assign → discover_create → assign → defer → END
# is at most 4 hops. A generous ceiling that only fires on an actual
# orchestration bug, not on a slow or looping model (the agent's own
# recursion_limit in agent.py handles that).
OUTER_RECURSION_LIMIT = 10

# OpenInference attrs so Phoenix renders the product parent as a CHAIN
# (not an unlabeled / unknown span) with a short outcome in the UI.
_SPAN_KIND_KEY: Final = SpanAttributes.OPENINFERENCE_SPAN_KIND
_SPAN_KIND_CHAIN: Final = OpenInferenceSpanKindValues.CHAIN.value
_OUTPUT_VALUE_KEY: Final = SpanAttributes.OUTPUT_VALUE


def _require_database_url(database_url: str | None) -> str:
    url = (database_url or os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        msg = "DATABASE_URL must be set for pipeline commands"
        raise RuntimeError(msg)
    return url


def _invoke_product_graph(
    *,
    database_url: str,
    product: RunProductRef,
    run_id: UUID,
    graph: Any,
    telemetry: Telemetry,
) -> dict[str, Any]:
    """Open a per-product connection and invoke the stage graph under one span.

    Hand-rolled ``pipeline.product`` parent: OpenInference instruments
    LangGraph into a span tree, but those spans are *not* attached as OTel
    current context. ``defer_node`` reads ``telemetry.current_trace_id()``
    (``get_current_span``), so without this wrap ``deferred_items`` rows get
    a null ``trace_id`` even when Phoenix shows a full tree.

    Args:
        database_url: App DB URL for the per-product connection.
        product: Catalog product this invocation decides about.
        run_id: Caller-minted run id shared with graph state and config.
        graph: Compiled stage graph from ``build_stage_graph``.
        telemetry: Active telemetry adapter (Phoenix or no-op).

    Returns:
        Final graph state dict for this product.
    """
    with connect_app(database_url) as conn:
        product_span = telemetry.start_span(
            "pipeline.product",
            attributes={
                _SPAN_KIND_KEY: _SPAN_KIND_CHAIN,
                "pipeline.product_id": str(product.product_id),
                "pipeline.run_id": str(run_id),
            },
        )
        try:
            outcome = graph.invoke(
                {
                    "product": product,
                    "run_id": str(run_id),
                    "discover_count": 0,
                },
                config={
                    "run_id": run_id,
                    "recursion_limit": OUTER_RECURSION_LIMIT,
                },
                context=StageDeps(
                    conn=conn,
                    telemetry=telemetry,
                    assign_agent=build_assign_stage_agent(conn),
                    discover_agent=build_discover_stage_agent(conn),
                ),
            )
        except Exception as exc:
            product_span.set_status(ok=False, description=str(exc))
            raise
        else:
            assign_result: StageResult = outcome["assign"]
            product_span.set_attribute(_OUTPUT_VALUE_KEY, assign_result.status)
            # Defer is a deliberate outcome, not a span failure — OK either way.
            product_span.set_status(ok=True)
            return outcome
        finally:
            product_span.end()


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
    """Select products, ensure a root exists, then run the two-stage graph over each.

    One connection per product (opened and closed around that product's
    stages, not held for the whole run) so the graph's tools all reuse the
    same live connection without an idle-in-transaction connection held
    across the entire run's LLM latency.  Sequential by design: product N's
    discover stage needs to see what product N-1's discover stage created.

    Args:
        ingest_filter: Category/keyword criteria (empty = every product).
        limit: Optional row cap; None means no limit.
        unassigned_only: Exclude products with an existing taxonomy leaf
            membership when True (the default). Pass False for
            ``--reassign``.
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Counts for the CLI summary line.
    """
    url = _require_database_url(database_url)

    # Select products and ensure a root category exist before the loop —
    # both are lightweight reads/single-writes that don't need to stay open
    # across LLM latency.
    with connect_app(url) as conn:
        selected = select_run_products(
            SelectRunProductsRequest(
                ingest_filter=ingest_filter,
                unassigned_only=unassigned_only,
                limit=limit,
            ),
            products=PsycopgRunProductRepository(conn),
        )
        ensure_root_category(
            categories=PsycopgCategoryRepository(conn),
            memberships=PsycopgMembershipRepository(conn),
            uow=PsycopgUnitOfWork(conn),
        )

    telemetry = configure_telemetry()
    graph = build_stage_graph()
    deferred_count = 0
    created_count = 0
    disagreement_count = 0

    for product in selected.products:
        run_id = uuid7()
        outcome = _invoke_product_graph(
            database_url=url,
            product=product,
            run_id=run_id,
            graph=graph,
            telemetry=telemetry,
        )

        assign_result: StageResult = outcome["assign"]
        if assign_result.status != "success":
            deferred_count += 1

        # Discover / create stats
        discover_result = outcome.get("discover")
        if discover_result is not None and discover_result.status == "success":
            created_count += 1
            # Check if the assign second pass disagreed with discover's leaf.
            discover_leaf = outcome.get("discover_leaf")
            assign_decision = outcome.get("assign_decision")
            if (
                discover_leaf is not None
                and isinstance(assign_decision, AssignDecision)
                and assign_decision.leaf_id != discover_leaf
            ):
                disagreement_count += 1

        logger.info(
            "pipeline product_id=%s run_id=%s assign_status=%s",
            product.product_id,
            run_id,
            assign_result.status,
        )

    return RunSummary(
        product_count=len(selected.products),
        deferred_count=deferred_count,
        created_count=created_count,
        disagreement_count=disagreement_count,
    )


__all__ = ["run_pipeline", "run_select_products"]
