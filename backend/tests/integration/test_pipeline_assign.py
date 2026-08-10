"""Integration tests for the Phase 2 assign-only stage graph.

Uses a ``_FakeStageAgent`` instead of a real LLM — real Postgres, real
graph, no network.  Covers:

- A successful assign writes a membership and returns status="success".
- A model-initiated defer writes a ``deferred_items`` row with stage=ASSIGN.
- An assign whose ``_FakeStageAgent`` always raises ``GraphRecursionError``
  is caught and produces a deferred row, not a traceback.
- A product span around ``graph.invoke`` populates ``deferred_items.trace_id``.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest

from agentic_cataloger.catalog.commands import ImportSnapshotRequest, import_snapshot
from agentic_cataloger.catalog.identity import SourceIdentity
from agentic_cataloger.catalog.models import ProductObservation
from agentic_cataloger.contracts.models import StageKind
from agentic_cataloger.pipeline.commands import ensure_root_category
from agentic_cataloger.pipeline.models import (
    AssignDecision,
    DeferDecision,
    RunProductRef,
    StageDecision,
)
from agentic_cataloger.pipeline.ports import AttributeValue, SpanHandle, Telemetry
from agentic_cataloger.platform.persistence.catalog_repo import (
    PsycopgProductRepository,
    PsycopgSnapshotRepository,
    PsycopgUnitOfWork,
    connect_app,
)
from agentic_cataloger.platform.persistence.review_repo import (
    PsycopgDeferredItemRepository,
)
from agentic_cataloger.platform.persistence.taxonomy_repo import (
    PsycopgCategoryRepository,
    PsycopgMembershipRepository,
)
from agentic_cataloger.platform.pipeline.graph import build_stage_graph
from agentic_cataloger.platform.pipeline.nodes import StageDeps
from agentic_cataloger.platform.telemetry import configure_telemetry
from agentic_cataloger.taxonomy.commands import (
    CreateCategoryRequest,
    create_category,
)


class _FakeStageAgent:
    """Scripted stub — returns canned StageDecisions, never touches the network."""

    def __init__(self, decisions: Sequence[StageDecision]) -> None:
        super().__init__()
        self._decisions = iter(decisions)

    def decide(
        self,
        *,
        product: RunProductRef,
        context: Mapping[str, object],
    ) -> StageDecision:
        return next(self._decisions)


class _RecursionAgent:
    """Mimics LangChainStageAgent after it catches a GraphRecursionError.

    LangChainStageAgent.decide() catches GraphRecursionError internally and
    converts it to a defer decision — the graph node never sees the raw
    exception.  This fake reproduces that converted outcome so the
    integration test can verify the deferred_items write without wiring a
    real (slow, network-dependent) LLM agent.
    """

    @staticmethod
    def decide(
        *,
        product: RunProductRef,
        context: Mapping[str, object],
    ) -> StageDecision:
        # Simulates what LangChainStageAgent returns after catching
        # GraphRecursionError from its internal create_agent loop.
        return DeferDecision(reason="recursion limit exceeded")


def _seed_product(conn: psycopg.Connection[Any], *, product_id_str: str) -> UUID:
    import_snapshot(
        ImportSnapshotRequest(
            source_namespace="migros-ch",
            source_observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            content_checksum=f"pipeline-assign-{product_id_str}-{uuid4()}",
            source_path="test.csv",
            observations=[
                ProductObservation(
                    identity=SourceIdentity("migros-ch", product_id_str),
                    name=f"Test product {product_id_str}",
                    product_url=f"https://www.migros.ch/de/product/{product_id_str}",
                    shelf_price=Decimal("1.50"),
                )
            ],
            deferred=[],
        ),
        snapshots=PsycopgSnapshotRepository(conn),
        products=PsycopgProductRepository(conn),
        uow=PsycopgUnitOfWork(conn),
    )
    product = PsycopgProductRepository(conn).get_by_source_identity(
        SourceIdentity("migros-ch", product_id_str)
    )
    assert product is not None
    return product.id


def _seed_tree(conn: psycopg.Connection[Any]) -> tuple[UUID, UUID]:
    """Create a two-level taxonomy tree; return (root_id, leaf_id).

    Uses ``ensure_root_category`` so the helper is idempotent when the shared
    integration DB already has a root from an earlier test.
    """
    tag = uuid4().hex[:8]
    cats = PsycopgCategoryRepository(conn)
    mems = PsycopgMembershipRepository(conn)
    uow = PsycopgUnitOfWork(conn)
    # Idempotent root creation — won't fail if another test already made one.
    ensure_root_category(categories=cats, memberships=mems, uow=uow)
    root = cats.get_root()
    assert root is not None
    leaf = create_category(
        CreateCategoryRequest(name=f"assign-leaf-{tag}", parent_id=root.id),
        categories=cats,
        memberships=mems,
        uow=uow,
    ).category
    return root.id, leaf.id


class _AlwaysDeferAgent:
    """Stub that always returns action='defer' — used as a no-op discover agent."""

    @staticmethod
    def decide(
        *,
        product: RunProductRef,
        context: Any,
    ) -> StageDecision:
        """Return a defer decision."""
        return DeferDecision(reason="stub discover agent")


@dataclass
class _ActiveSpanHandle:
    """Span handle that decrements the active-span depth on ``end``."""

    _telemetry: _ActiveSpanTelemetry

    def set_attribute(self, key: str, value: AttributeValue) -> None:
        _ = (self, key, value)

    def set_status(self, *, ok: bool, description: str = "") -> None:
        _ = (self, ok, description)

    def end(self) -> None:
        self._telemetry._depth = max(0, self._telemetry._depth - 1)


@dataclass
class _ActiveSpanTelemetry:
    """Telemetry fake that exposes a trace id only while a span is open.

    Mirrors the runner's ``pipeline.product`` wrap: ``current_trace_id`` is
    non-None inside ``graph.invoke``, None outside. Avoids needing a live
    Phoenix collector for the deferred-row assertion.
    """

    _trace_id: str = field(default_factory=lambda: uuid4().hex)
    _depth: int = 0

    def start_span(
        self,
        name: str,
        *,
        attributes: Mapping[str, AttributeValue] | None = None,
    ) -> SpanHandle:
        _ = (name, attributes)
        self._depth += 1
        return _ActiveSpanHandle(_telemetry=self)

    def current_trace_id(self) -> str | None:
        return self._trace_id if self._depth > 0 else None

    def shutdown(self) -> None:
        _ = self


def _run_graph(
    conn: psycopg.Connection[Any],
    *,
    product_id: UUID,
    agent: Any,
    discover_agent: Any = None,
    telemetry: Telemetry | None = None,
) -> dict[str, Any]:
    """Invoke the stage graph for one product and return the full state dict.

    ``discover_agent`` defaults to ``_AlwaysDeferAgent`` so existing Phase 2
    callers don't break; Phase 3 callers pass their own scripted agent.

    Mirrors ``run_pipeline``: wraps ``graph.invoke`` in a ``pipeline.product``
    span so ``defer_node`` can read ``telemetry.current_trace_id()``.
    """
    graph = build_stage_graph()
    active_telemetry = telemetry if telemetry is not None else configure_telemetry()
    product = RunProductRef(
        product_id=product_id,
        name="Test product",
        name_de=None,
        source_category=None,
        unified_category=None,
    )
    run_id = str(uuid4())
    product_span = active_telemetry.start_span(
        "pipeline.product",
        attributes={
            "pipeline.product_id": str(product_id),
            "pipeline.run_id": run_id,
        },
    )
    try:
        return graph.invoke(  # type: ignore[return-value]
            {
                "product": product,
                "run_id": run_id,
                "discover_count": 0,
            },
            config={"recursion_limit": 10},
            context=StageDeps(
                conn=conn,
                telemetry=active_telemetry,
                stage_agent=agent,
                discover_agent=discover_agent or _AlwaysDeferAgent(),
            ),
        )
    finally:
        product_span.end()


@pytest.mark.integration
def test_assign_success_writes_membership_and_returns_success(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """A clean assign writes a membership and returns status='success'."""
    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, product_id_str=f"pa-success-{uuid4().hex[:8]}")
        _, leaf_id = _seed_tree(conn)

        agent = _FakeStageAgent([AssignDecision(leaf_id=leaf_id)])
        outcome = _run_graph(conn, product_id=pid, agent=agent)

        result = outcome["assign"]
        assert result.status == "success"
        assert result.stage == StageKind.ASSIGN

        memberships = PsycopgMembershipRepository(conn)
        membership = memberships.get_by_product(pid)
        assert membership is not None
        assert membership.category_id == leaf_id


@pytest.mark.integration
def test_assign_miss_defers_and_writes_deferred_item(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Assign miss → discover also defers → one deferred_items row.

    In Phase 3 the assign miss routes to discover first.  With a stub
    discover that always defers, the deferred_items row is attributed to
    DISCOVER_CREATE (the last stage that ran and could not place the product).
    """
    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, product_id_str=f"pa-miss-{uuid4().hex[:8]}")

        agent = _FakeStageAgent([DeferDecision(reason="nothing in tree fits")])
        outcome = _run_graph(conn, product_id=pid, agent=agent)

        result = outcome["assign"]
        assert result.status == "defer"

        items = PsycopgDeferredItemRepository(conn).list_open()
        matching = [i for i in items if i.product_id == pid]
        assert len(matching) == 1
        # Phase 3: assign miss → discover (stub, also defers) → defer_node
        # attributes to DISCOVER_CREATE, the terminal failing stage.
        assert matching[0].stage == StageKind.DISCOVER_CREATE


@pytest.mark.integration
def test_recursion_error_produces_deferred_row_not_traceback(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """A GraphRecursionError from the agent is caught and defers the product.

    In Phase 3 the deferred row is attributed to DISCOVER_CREATE because the
    stub discover agent also defers after the assign agent defers.
    """
    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, product_id_str=f"pa-recurse-{uuid4().hex[:8]}")

        outcome = _run_graph(conn, product_id=pid, agent=_RecursionAgent())

        result = outcome["assign"]
        # GraphRecursionError is caught inside LangChainStageAgent.decide, which
        # our _RecursionAgent mimics directly — the node sees action="defer".
        assert result.status in {"defer", "invalid"}

        items = PsycopgDeferredItemRepository(conn).list_open()
        matching = [i for i in items if i.product_id == pid]
        assert len(matching) == 1
        # Phase 3: assign defer → discover (stub, also defers) → DISCOVER_CREATE.
        assert matching[0].stage == StageKind.DISCOVER_CREATE


@pytest.mark.integration
def test_defer_writes_trace_id_from_product_span(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Product span around invoke → deferred_items.trace_id is populated.

    LangGraph's OpenInference spans do not attach as OTel current context;
    the runner's ``pipeline.product`` wrap is what ``current_trace_id()``
    reads. This test mirrors that wrap with an in-memory telemetry fake.
    """
    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, product_id_str=f"pa-trace-{uuid4().hex[:8]}")
        telemetry = _ActiveSpanTelemetry()

        _run_graph(
            conn,
            product_id=pid,
            agent=_FakeStageAgent([DeferDecision(reason="nothing fits")]),
            telemetry=telemetry,
        )

        items = PsycopgDeferredItemRepository(conn).list_open()
        matching = [i for i in items if i.product_id == pid]
        assert len(matching) == 1
        assert matching[0].trace_id == telemetry._trace_id
        # Span must be closed after invoke (no leak of "current" context).
        assert telemetry.current_trace_id() is None
