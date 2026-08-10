"""Select the products a pipeline run operates on, plus pure routing rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.contracts.models import StageKind
from agentic_cataloger.pipeline.models import (
    RunProductRef,
    SelectRunProductsResult,
    StageDecision,
)
from agentic_cataloger.pipeline.ports import RunProductRepository
from agentic_cataloger.review.commands import DeferItemRequest
from agentic_cataloger.review.models import ReasonCode
from agentic_cataloger.taxonomy.commands import CreateCategoryRequest, create_category
from agentic_cataloger.taxonomy.ports import (
    CategoryRepository,
    MembershipRepository,
    TaxonomyUnitOfWork,
)


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


def route_after_assign(
    decision: StageDecision,
    *,
    discover_count: int,
) -> Literal["done", "discover_create", "defer"]:
    """Decide where the graph goes after an assign-stage decision.

    This is the checkable half of roadmap 2.6 ("prefer matching an existing
    category before creating") and the defer contract: any decision that
    isn't a clean ``action="assign"`` with a ``leaf_id`` is a miss, and a
    miss reaches ``discover_create`` only while ``discover_count`` is below
    ``_MAX_DISCOVER_ITERATIONS``; further misses defer instead of
    ping-ponging.

    Args:
        decision: The stage's decision (model output, or a node-level
            override such as an invalid write turned into a synthetic
            ``action="defer"``).
        discover_count: How many times discover/create has already run for
            this product in this graph invocation.

    Returns:
        ``"done"`` on a clean assign, ``"discover_create"`` on a miss with
        discover budget remaining, ``"defer"`` once the discover budget is
        exhausted.
    """
    if decision.action == "assign" and decision.leaf_id is not None:
        return "done"
    if discover_count >= _MAX_DISCOVER_ITERATIONS:
        return "defer"
    return "discover_create"


def build_defer_request(
    *,
    product: RunProductRef,
    stage: StageKind,
    decision_or_error: StageDecision | Exception,
    attempt_count: int,
    trace_id: str | None,
) -> DeferItemRequest:
    """Build the request that records why a stage won't guess about a product.

    Two different things produce a defer and only one has a model in the
    loop: a model-initiated miss (``StageDecision`` with a free-text
    ``reason``) and a node-initiated failure (an ``Exception`` the node
    caught — invalid structured output, a retry budget exhausted, a
    recursion limit). Both converge on this one builder, which is what
    makes "every terminal path writes exactly one deferred_items row"
    checkable.

    Args:
        product: The product this stage attempt was working on.
        stage: Which stage deferred.
        decision_or_error: The model's ``StageDecision`` (model-initiated
            defer) or an ``Exception`` the node caught (node-initiated).
        attempt_count: How many times the model was actually asked (>= 1).
        trace_id: Phoenix/OTel trace id, if telemetry is active.

    Returns:
        Request ready for ``review.commands.defer_item``.
    """
    if isinstance(decision_or_error, Exception):
        reason_code = ReasonCode.UNKNOWN
        reason = str(decision_or_error)
    else:
        reason_code = ReasonCode.DEFER
        reason = decision_or_error.reason

    payload_snapshot: dict[str, object] = {
        "product_name": product.name,
        "product_name_de": product.name_de,
        "source_category": product.source_category,
        "unified_category": product.unified_category,
        "reason": reason,
    }
    return DeferItemRequest(
        product_id=product.product_id,
        stage=stage,
        reason_code=reason_code,
        attempt_count=attempt_count,
        payload_snapshot=payload_snapshot,
        trace_id=trace_id,
    )


def ensure_root_category(
    *,
    categories: CategoryRepository,
    memberships: MembershipRepository,
    uow: TaxonomyUnitOfWork,
) -> None:
    """Ensure a root category exists before a pipeline run starts.

    Creates "All products" when no root is present so the model never
    needs to reason about roots, and a ``RootAlreadyExistsError`` can
    never surface mid-run from the discover stage.  Called once before
    the product loop (not per product).

    Args:
        categories: Category repository.
        memberships: Membership repository (required by ``create_category``
            for the leaf-demotion check, which is a no-op for a root).
        uow: Unit of work for a transactional write.
    """
    if categories.get_root() is not None:
        return
    create_category(
        CreateCategoryRequest(name="All products"),
        categories=categories,
        memberships=memberships,
        uow=uow,
    )


_MAX_CREATE_LEVELS = 5
_MAX_DISCOVER_ITERATIONS = 3


def validate_create_proposal(decision: StageDecision) -> None:
    """Validate a discover stage's create proposal before calling ``create_category``.

    A create with no rejected-candidate evidence is refused (roadmap 2.6 —
    enforced in the node, not only in the prompt). A path longer than
    ``_MAX_CREATE_LEVELS`` is also refused to keep the tree shallow and bounded
    (design discussion: cap new levels at ``_MAX_CREATE_LEVELS``; deeper than
    that, defer).

    Args:
        decision: The discover stage's decision (must have action="create").

    Raises:
        ValueError: When ``rejected`` is empty, ``names`` is empty, or the
            path is deeper than ``_MAX_CREATE_LEVELS``.
    """
    if not decision.rejected:
        msg = (
            "create proposal must include at least one rejected candidate "
            "(roadmap 2.6 — a create with no evidence is refused)"
        )
        raise ValueError(msg)
    if not decision.names:
        msg = "create proposal must include at least one category name"
        raise ValueError(msg)
    if len(decision.names) > _MAX_CREATE_LEVELS:
        msg = (
            f"create path must be at most {_MAX_CREATE_LEVELS} levels; "
            f"got {len(decision.names)}"
        )
        raise ValueError(msg)


__all__ = [
    "SelectRunProductsRequest",
    "build_defer_request",
    "ensure_root_category",
    "route_after_assign",
    "select_run_products",
    "validate_create_proposal",
]
