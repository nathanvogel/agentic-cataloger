"""Graph nodes for the per-product pipeline StateGraph.

``assign_node`` calls the bound ``StageAgent`` and — on a clean assign —
writes the membership itself through the live connection's repositories (an
invariant-enforced-twice pattern already used elsewhere: the tool the model
calls can write the same row, but the node is the guaranteed, idempotent
write site). ``discover_node`` validates the create proposal and loops
``create_category`` down the proposed path. ``defer_node`` is the single
write site for every kind of miss, model-initiated or node-initiated.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Literal, NotRequired, TypedDict, cast
from uuid import UUID

import psycopg
from langgraph.graph import END
from langgraph.runtime import Runtime

from agentic_cataloger.contracts.models import StageKind, StageResult
from agentic_cataloger.pipeline.commands import (
    build_defer_request,
    validate_create_proposal,
)
from agentic_cataloger.pipeline.commands import (
    route_after_assign as _route_after_assign,
)
from agentic_cataloger.pipeline.models import (
    AssignDecision,
    CreateDecision,
    DeferDecision,
    RunProductRef,
    StageDecision,
)
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
    CreateCategoryRequest,
    assign_product_to_leaf,
    create_category,
)
from agentic_cataloger.taxonomy.errors import TaxonomyError

logger = logging.getLogger(__name__)


class RunState(TypedDict):
    """Per-product graph state.

    ``assign_decision``/``assign_error``/``assign`` are set by
    ``assign_node``; ``discover_decision``/``discover_error``/``discover``/
    ``discover_leaf`` are set by ``discover_node``.  Both nodes share
    ``discover_count`` which caps assign↔discover ping-ponging.
    """

    product: RunProductRef
    run_id: str
    discover_count: int
    # Set by assign_node:
    assign_decision: NotRequired[StageDecision]
    assign_error: NotRequired[Exception]
    assign: NotRequired[StageResult]
    # Set by discover_node (Phase 3):
    discover_decision: NotRequired[StageDecision]
    discover_error: NotRequired[Exception]
    discover: NotRequired[StageResult]
    discover_leaf: NotRequired[UUID]


@dataclass(frozen=True, slots=True)
class StageDeps:
    """Per-invocation context: one live connection, telemetry, and both agents.

    ``conn`` is scoped to one product (opened and closed by the runner's
    per-product loop) — every node in one graph invocation shares it.
    ``assign_agent`` is the assign stage; ``discover_agent`` is the
    discover/create stage.
    """

    conn: psycopg.Connection[Any]
    telemetry: Telemetry
    assign_agent: StageAgent
    discover_agent: StageAgent


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

    On the first pass, ``state["discover_count"]`` is 0 and context is
    empty.  After discover_node runs and sets ``discover_leaf``, the created
    leaf is passed as context so the model can consider it alongside its own
    search results.

    Args:
        state: Current graph state.
        runtime: Node runtime carrying ``StageDeps``.

    Returns:
        State update: ``assign`` (telemetry-shaped outcome),
        ``assign_decision`` (used for routing and, on a miss, deferral),
        and ``assign_error`` when the write itself was rejected.
    """
    # Second pass: include the discover-created leaf as a labeled candidate.
    context: dict[str, object] = {}
    discover_leaf = state.get("discover_leaf")
    if discover_leaf is not None:
        context["suggested_leaf_id"] = str(discover_leaf)
        context["suggested_leaf_note"] = (
            "This leaf was just created by the discover stage for this product. "
            "Consider it alongside your own search, but choose independently."
        )

    decision = runtime.context.assign_agent.decide(
        product=state["product"],
        context=context,
    )
    attempt = runtime.execution_info.node_attempt if runtime.execution_info else 1
    updates: dict[str, Any] = {"assign_decision": decision}
    status: Literal["success", "defer", "invalid"]

    if isinstance(decision, AssignDecision):
        try:
            _write_assignment(
                runtime.context.conn,
                product_id=state["product"].product_id,
                leaf_id=decision.leaf_id,
            )
        except TaxonomyError as exc:
            status = "invalid"
            updates["assign_decision"] = DeferDecision(reason=str(exc))
            updates["assign_error"] = exc
        else:
            status = "success"
    elif isinstance(decision, DeferDecision):
        status = "defer"
    else:
        # CreateDecision — the assign stage schema never offers "create",
        # so this is a node-level rejection.
        status = "invalid"
        exc = ValueError(
            f"assign stage returned unexpected decision {type(decision).__name__!r}"
        )
        updates["assign_decision"] = DeferDecision(reason=str(exc))
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
        state: Current graph state (``assign_decision``/``discover_count``
            are always set by the time this runs, since it only fires
            after ``assign_node``).

    Returns:
        Node name to run next: ``END`` on a clean assign, otherwise
        ``"discover_create"`` or ``"defer"``.
    """
    outcome = _route_after_assign(
        cast(StageDecision, state.get("assign_decision")),
        discover_count=state["discover_count"],
    )
    return END if outcome == "done" else outcome


def discover_node(state: RunState, runtime: Runtime[StageDeps]) -> dict[str, Any]:
    """Propose and create new categories when the assign stage found no fit.

    Calls the discover agent, validates its proposal, then loops
    ``create_category`` down the proposed path.  On a validation failure or
    taxonomy error, the node marks the result as ``status="invalid"`` so
    LangGraph's ``RetryPolicy`` can retry before routing to ``defer``.

    Args:
        state: Current graph state.
        runtime: Node runtime carrying ``StageDeps``.

    Returns:
        State update: ``discover_count`` (incremented after this node),
        ``discover_decision``, ``discover`` (the stage result), and
        ``discover_leaf`` (UUID of the created leaf, when creation succeeds).
    """
    decision = runtime.context.discover_agent.decide(
        product=state["product"],
        context={},
    )
    attempt = runtime.execution_info.node_attempt if runtime.execution_info else 1
    updates: dict[str, Any] = {
        "discover_decision": decision,
        "discover_count": state["discover_count"] + 1,
    }

    if isinstance(decision, DeferDecision):
        updates["discover"] = StageResult(
            run_id=state["run_id"],
            stage=StageKind.DISCOVER_CREATE,
            attempt=attempt,
            status="defer",
            reason=decision.reason,
        )
        return updates

    if not isinstance(decision, CreateDecision):
        decision_type = type(decision).__name__
        exc_msg = f"discover stage returned unexpected decision {decision_type!r}"
        logger.warning(exc_msg)
        updates["discover_decision"] = DeferDecision(reason=exc_msg)
        updates["discover"] = StageResult(
            run_id=state["run_id"],
            stage=StageKind.DISCOVER_CREATE,
            attempt=attempt,
            status="invalid",
            reason=exc_msg,
        )
        return updates

    # Validate the create proposal before touching the DB.
    try:
        validate_create_proposal(decision)
    except ValueError as exc:
        logger.warning(
            "Discover proposal invalid for product_id=%s: %s",
            state["product"].product_id,
            exc,
        )
        updates["discover_decision"] = DeferDecision(reason=str(exc))
        updates["discover_error"] = exc
        updates["discover"] = StageResult(
            run_id=state["run_id"],
            stage=StageKind.DISCOVER_CREATE,
            attempt=attempt,
            status="invalid",
            reason=str(exc),
        )
        return updates

    # Loop create_category down the proposed path.
    conn = runtime.context.conn
    cats = PsycopgCategoryRepository(conn)
    mems = PsycopgMembershipRepository(conn)
    uow = PsycopgUnitOfWork(conn)

    parent_id = decision.parent_id
    leaf_id: UUID | None = None

    try:
        for name in decision.names:
            result = create_category(
                CreateCategoryRequest(name=name, parent_id=parent_id),
                categories=cats,
                memberships=mems,
                uow=uow,
            )
            leaf_id = result.category.id
            parent_id = result.category.id
    except TaxonomyError as exc:
        logger.warning(
            "Discover create_category failed for product_id=%s: %s",
            state["product"].product_id,
            exc,
        )
        updates["discover_decision"] = DeferDecision(reason=str(exc))
        updates["discover_error"] = exc
        updates["discover"] = StageResult(
            run_id=state["run_id"],
            stage=StageKind.DISCOVER_CREATE,
            attempt=attempt,
            status="invalid",
            reason=str(exc),
        )
        return updates

    if leaf_id is not None:
        updates["discover_leaf"] = leaf_id

    updates["discover"] = StageResult(
        run_id=state["run_id"],
        stage=StageKind.DISCOVER_CREATE,
        attempt=attempt,
        status="success",
    )
    return updates


def route_after_discover(state: RunState) -> str:
    """Conditional-edge function: route after the discover_create node.

    Args:
        state: Current graph state (``discover`` and ``discover_decision``
            are always set by the time this runs).

    Returns:
        ``"assign"`` when discover created a leaf (status="success");
        ``"defer"`` when discover failed or the proposal was invalid.
    """
    discover_result = cast(StageResult | None, state.get("discover"))
    if discover_result is not None and discover_result.status == "success":
        return "assign"
    return "defer"


def defer_node(state: RunState, runtime: Runtime[StageDeps]) -> dict[str, Any]:
    """Record that a stage won't guess about this product.

    The single write site for every kind of miss — model-initiated or
    node-initiated — from either the assign or discover stage.  Attributes
    the defer to discover when discover ran and did not succeed (status !=
    "success"); otherwise attributes it to assign.

    Args:
        state: Current graph state.
        runtime: Node runtime carrying ``StageDeps``.

    Returns:
        Empty state update (this is a terminal node).
    """
    discover_result = cast(StageResult | None, state.get("discover"))
    if discover_result is not None and discover_result.status != "success":
        # Discover stage deferred or failed — attribute to DISCOVER_CREATE.
        stage = StageKind.DISCOVER_CREATE
        decision_or_error: StageDecision | Exception = state.get(
            "discover_error"
        ) or cast(StageDecision, state.get("discover_decision"))
        attempt_count = discover_result.attempt
    else:
        # Assign stage deferred (first pass miss with no discover, or second
        # pass miss after discover succeeded) — attribute to ASSIGN.
        stage = StageKind.ASSIGN
        decision_or_error = state.get("assign_error") or cast(
            StageDecision, state.get("assign_decision")
        )
        assign_result = cast(StageResult | None, state.get("assign"))
        attempt_count = assign_result.attempt if assign_result else 1

    request = build_defer_request(
        product=state["product"],
        stage=stage,
        decision_or_error=decision_or_error,
        attempt_count=attempt_count,
        trace_id=runtime.context.telemetry.current_trace_id(),
    )
    defer_item(
        request,
        items=PsycopgDeferredItemRepository(runtime.context.conn),
        uow=PsycopgUnitOfWork(runtime.context.conn),
    )
    return {}


__all__ = [
    "RunState",
    "StageDeps",
    "assign_node",
    "defer_node",
    "discover_node",
    "route_after_assign",
    "route_after_discover",
]
