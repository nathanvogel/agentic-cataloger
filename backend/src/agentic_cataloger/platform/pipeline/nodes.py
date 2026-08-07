"""Graph nodes for the per-product pipeline StateGraph (Phase 2: assign, defer).

``assign_node`` calls the bound ``StageAgent``, wraps the call in a
non-LLM-kind ``pipeline.stage`` span, and — on a clean assign — writes the
membership itself through the live connection's repositories (an
invariant-enforced-twice pattern already used elsewhere in this codebase:
the tool the model calls can write the same row, but the node is the
guaranteed, idempotent write site). ``defer_node`` is the single write site
for every kind of miss, model-initiated or node-initiated.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict, cast
from uuid import UUID

import psycopg
from langgraph.graph import END
from langgraph.runtime import Runtime

from agentic_cataloger.contracts.models import StageKind, StageResult
from agentic_cataloger.pipeline.commands import build_defer_request
from agentic_cataloger.pipeline.commands import (
    route_after_assign as _route_after_assign,
)
from agentic_cataloger.pipeline.models import RunProductRef, StageDecision
from agentic_cataloger.pipeline.ports import StageAgent, Telemetry
from agentic_cataloger.platform.persistence.catalog_repo import (
    PsycopgProductRepository,
    PsycopgUnitOfWork,
)
from agentic_cataloger.platform.persistence.review_repo import (
    PsycopgDeferredItemRepository,
)
from agentic_cataloger.platform.persistence.taxonomy_repo import (
    PsycopgCategoryRepository,
    PsycopgMembershipRepository,
)
from agentic_cataloger.review.commands import defer_item
from agentic_cataloger.taxonomy.commands import (
    AssignProductRequest,
    assign_product_to_leaf,
)
from agentic_cataloger.taxonomy.errors import TaxonomyError


class RunState(TypedDict):
    """Per-product graph state.

    ``assign_decision``/``assign_error``/``assign`` are set by
    ``assign_node``; ``defer_node`` and the conditional edge read them back.
    """

    product: RunProductRef
    run_id: str
    discover_ran: bool
    assign_decision: NotRequired[StageDecision]
    assign_error: NotRequired[Exception]
    assign: NotRequired[StageResult]


@dataclass(frozen=True, slots=True)
class StageDeps:
    """Per-invocation context: one live connection, telemetry, and the agent(s).

    ``conn`` is scoped to one product (opened and closed by the runner's
    per-product loop) — every node in one graph invocation shares it.
    """

    conn: psycopg.Connection[Any]
    telemetry: Telemetry
    stage_agent: StageAgent


def _decide(runtime: Runtime[StageDeps], product: RunProductRef) -> StageDecision:
    """Call the bound stage agent inside one non-LLM-kind ``pipeline.stage`` span.

    Args:
        runtime: Node runtime carrying ``StageDeps``.
        product: Product this stage attempt is deciding about.

    Returns:
        The stage's decision.
    """
    handle = runtime.context.telemetry.start_span(
        "pipeline.stage",
        attributes={"pipeline.stage.kind": str(StageKind.ASSIGN)},
    )
    try:
        return runtime.context.stage_agent.decide(product=product, context={})
    finally:
        handle.end()


def _write_assignment(
    conn: psycopg.Connection[Any],
    *,
    product_id: UUID,
    leaf_id: UUID,
) -> None:
    """Assign ``product_id`` to ``leaf_id`` through the live connection's repositories.

    Args:
        conn: Live psycopg connection for this product.
        product_id: Catalog product to assign.
        leaf_id: Target leaf category.
    """
    assign_product_to_leaf(
        AssignProductRequest(product_id=product_id, leaf_id=leaf_id),
        categories=PsycopgCategoryRepository(conn),
        memberships=PsycopgMembershipRepository(conn),
        products=PsycopgProductRepository(conn),
        uow=PsycopgUnitOfWork(conn),
    )


def assign_node(state: RunState, runtime: Runtime[StageDeps]) -> dict[str, Any]:
    """Decide-then-write the assign stage for one product.

    Args:
        state: Current graph state.
        runtime: Node runtime carrying ``StageDeps``.

    Returns:
        State update: ``assign`` (telemetry-shaped outcome),
        ``assign_decision`` (used for routing and, on a miss, deferral),
        and ``assign_error`` when the write itself was rejected.
    """
    decision = _decide(runtime, state["product"])
    attempt = runtime.execution_info.node_attempt if runtime.execution_info else 1
    updates: dict[str, Any] = {"assign_decision": decision}
    status: Literal["success", "defer", "invalid"]

    if decision.action == "assign" and decision.leaf_id is not None:
        try:
            _write_assignment(
                runtime.context.conn,
                product_id=state["product"].product_id,
                leaf_id=decision.leaf_id,
            )
        except TaxonomyError as exc:
            status = "invalid"
            updates["assign_decision"] = StageDecision(action="defer", reason=str(exc))
            updates["assign_error"] = exc
        else:
            status = "success"
    elif decision.action == "defer":
        status = "defer"
    else:
        # action="create" (or any other shape) — the assign stage's schema
        # never offers "create", so this is a node-level rejection, not a
        # model-initiated defer.
        status = "invalid"
        exc = ValueError(f"assign stage returned unexpected action {decision.action!r}")
        updates["assign_decision"] = StageDecision(action="defer", reason=str(exc))
        updates["assign_error"] = exc

    updates["assign"] = StageResult(
        run_id=state["run_id"],
        stage=StageKind.ASSIGN,
        attempt=attempt,
        status=status,
        reason=updates["assign_decision"].reason,
    )
    return updates


def route_after_assign(state: RunState) -> str:
    """Conditional-edge function: delegate to the pure domain routing rule.

    Args:
        state: Current graph state (``assign_decision``/``discover_ran``
            are always set by the time this runs, since it only fires
            after ``assign_node``).

    Returns:
        ``END`` on a clean assign; otherwise the domain's routing literal
        (``"discover_create"``/``"defer"``) for ``graph.py``'s path map to
        resolve into an actual node name.
    """
    # assign_node always sets assign_decision before this edge fires
    outcome = _route_after_assign(
        cast(StageDecision, state.get("assign_decision")),
        discover_ran=state["discover_ran"],
    )
    return END if outcome == "done" else outcome


def defer_node(state: RunState, runtime: Runtime[StageDeps]) -> dict[str, Any]:
    """Record that the assign stage won't guess about this product.

    The single write site for every kind of miss — a model-initiated defer
    (``assign_decision``) or a node-initiated one (``assign_error``, when
    present, takes precedence so the recorded reason is the real failure).

    Args:
        state: Current graph state.
        runtime: Node runtime carrying ``StageDeps``.

    Returns:
        Empty state update (this is a terminal node).
    """
    # assign_node always sets assign_decision (and optionally assign_error)
    # before defer_node fires — cast satisfies pyright's NotRequired check.
    decision_or_error: StageDecision | Exception = state.get("assign_error") or cast(
        StageDecision, state.get("assign_decision")
    )
    assign_result = cast(StageResult, state.get("assign"))
    request = build_defer_request(
        product=state["product"],
        stage=StageKind.ASSIGN,
        decision_or_error=decision_or_error,
        attempt_count=assign_result.attempt,
        trace_id=runtime.context.telemetry.current_trace_id(),
    )
    defer_item(
        request,
        items=PsycopgDeferredItemRepository(runtime.context.conn),
        uow=PsycopgUnitOfWork(runtime.context.conn),
    )
    return {}


__all__ = ["RunState", "StageDeps", "assign_node", "defer_node", "route_after_assign"]
