"""Domain tests for pipeline.commands routing/defer-request rules (fakes)."""

from __future__ import annotations

from uuid import uuid4

from agentic_cataloger.contracts.models import StageKind
from agentic_cataloger.pipeline.commands import build_defer_request, route_after_assign
from agentic_cataloger.pipeline.models import (
    AssignDecision,
    DeferDecision,
    RunProductRef,
)
from agentic_cataloger.review.models import ReasonCode


def _product() -> RunProductRef:
    return RunProductRef(
        product_id=uuid4(),
        name="Vollmilch",
        name_de="Vollmilch",
        source_category="Milchprodukte",
        unified_category="dairy",
    )


def test_route_after_assign_success_is_done() -> None:
    """A clean assign routes to "done" regardless of discover_count."""
    decision = AssignDecision(leaf_id=uuid4())

    assert route_after_assign(decision, discover_count=0) == "done"
    assert route_after_assign(decision, discover_count=3) == "done"


def test_route_after_assign_miss_routes_to_discover_while_budget_remains() -> None:
    """A miss routes to discover while discover_count is below the cap."""
    decision = DeferDecision(reason="nothing fits")

    assert route_after_assign(decision, discover_count=0) == "discover"
    assert route_after_assign(decision, discover_count=1) == "discover"
    assert route_after_assign(decision, discover_count=2) == "discover"


def test_route_after_assign_miss_defers_once_discover_budget_exhausted() -> None:
    """A miss defers once discover_count reaches the iteration cap."""
    decision = DeferDecision(reason="still nothing fits")

    assert route_after_assign(decision, discover_count=3) == "defer"
    assert route_after_assign(decision, discover_count=4) == "defer"


def test_route_after_assign_defer_is_a_miss() -> None:
    """DeferDecision is treated like any other miss."""
    decision = DeferDecision(reason="assign response missing leaf_id")

    assert route_after_assign(decision, discover_count=0) == "discover"
    assert route_after_assign(decision, discover_count=3) == "defer"


def test_build_defer_request_from_model_decision_uses_defer_reason_code() -> None:
    """A DeferDecision (model-initiated defer) maps to ReasonCode.DEFER."""
    product = _product()
    decision = DeferDecision(reason="nothing in the tree fits")

    request = build_defer_request(
        product=product,
        stage=StageKind.ASSIGN,
        decision_or_error=decision,
        attempt_count=1,
        trace_id="trace-123",
    )

    assert request.product_id == product.product_id
    assert request.stage == StageKind.ASSIGN
    assert request.reason_code == ReasonCode.DEFER
    assert request.attempt_count == 1
    assert request.trace_id == "trace-123"
    assert request.payload_snapshot["reason"] == "nothing in the tree fits"
    assert request.payload_snapshot["product_name"] == product.name


def test_build_defer_request_from_exception_uses_unknown_reason_code() -> None:
    """A caught Exception (node-initiated defer) maps to ReasonCode.UNKNOWN."""
    product = _product()
    error = ValueError("leaf 00000000-0000-0000-0000-000000000000 not found")

    request = build_defer_request(
        product=product,
        stage=StageKind.ASSIGN,
        decision_or_error=error,
        attempt_count=3,
        trace_id=None,
    )

    assert request.reason_code == ReasonCode.UNKNOWN
    assert request.attempt_count == 3
    assert request.trace_id is None
    assert request.payload_snapshot["reason"] == str(error)
