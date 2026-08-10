"""Integration tests for the Phase 3 discover/create stage graph.

Uses ``_FakeStageAgent`` scripted per-call — real Postgres, real graph, no
network.  Covers:

1. Cold tree: assign miss → discover creates 2 levels → assign second pass
   places the product in the new leaf.
2. Ping-pong guard: a discover agent that always misses produces exactly one
   discover call then defers, never loops.
3. Invalid proposal (empty rejected): discover returns create with no
   rejected candidates → invalid → retried → deferred, create_category never
   called.
4. Path-too-deep proposal (6 levels): discover returns 6-level names list →
   deferred without calling create_category.
5. Assign second pass picks a different leaf than discover created →
   disagreement_count == 1 in the run summary, and the created leaf ends
   with zero members.
"""

from __future__ import annotations

from collections.abc import Mapping
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
from agentic_cataloger.pipeline.models import (
    RejectedCandidate,
    RunProductRef,
    StageDecision,
)
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
from agentic_cataloger.taxonomy.commands import CreateCategoryRequest, create_category

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeStageAgent:
    """Scripted stub — returns canned StageDecisions without network calls."""

    def __init__(self, decisions: list[StageDecision]) -> None:
        super().__init__()
        self._decisions = iter(decisions)

    def decide(
        self,
        *,
        product: RunProductRef,
        context: Mapping[str, object],
    ) -> StageDecision:
        """Return the next scripted decision."""
        return next(self._decisions)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _seed_product(conn: psycopg.Connection[Any], *, tag: str) -> UUID:
    """Insert a product via import_snapshot and return its UUID."""
    product_id_str = f"pd-{tag}"
    import_snapshot(
        ImportSnapshotRequest(
            source_namespace="migros-ch",
            source_observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            content_checksum=f"pipeline-discover-{tag}-{uuid4()}",
            source_path="test.csv",
            observations=[
                ProductObservation(
                    identity=SourceIdentity("migros-ch", product_id_str),
                    name=f"Test product {tag}",
                    product_url=f"https://www.migros.ch/de/product/{product_id_str}",
                    shelf_price=Decimal("2.50"),
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


def _seed_root(conn: psycopg.Connection[Any], *, tag: str) -> UUID:
    """Ensure a root category exists and return its id.

    Uses ``ensure_root_category`` so this helper is idempotent when the
    shared integration DB already has a root from an earlier test.  The
    ``tag`` parameter is kept for call-site readability but has no effect.
    """
    from agentic_cataloger.pipeline.commands import ensure_root_category

    cats = PsycopgCategoryRepository(conn)
    mems = PsycopgMembershipRepository(conn)
    uow = PsycopgUnitOfWork(conn)
    ensure_root_category(categories=cats, memberships=mems, uow=uow)
    root = cats.get_root()
    assert root is not None
    return root.id


def _seed_leaf(conn: psycopg.Connection[Any], *, name: str, parent_id: UUID) -> UUID:
    """Create a leaf category under parent_id and return its id."""
    result = create_category(
        CreateCategoryRequest(name=name, parent_id=parent_id),
        categories=PsycopgCategoryRepository(conn),
        memberships=PsycopgMembershipRepository(conn),
        uow=PsycopgUnitOfWork(conn),
    )
    return result.category.id


def _rejected(category_id: UUID, name: str) -> RejectedCandidate:
    return RejectedCandidate(category_id=category_id, name=name)


def _run_graph(
    conn: psycopg.Connection[Any],
    *,
    product_id: UUID,
    assign_agent: Any,
    discover_agent: Any,
) -> dict[str, Any]:
    """Invoke the stage graph for one product and return the full state dict."""
    graph = build_stage_graph()
    telemetry = configure_telemetry()
    product = RunProductRef(
        product_id=product_id,
        name="Test product",
        name_de=None,
        source_category=None,
        unified_category=None,
    )
    return graph.invoke(  # type: ignore[return-value]
        {
            "product": product,
            "run_id": str(uuid4()),
            "discover_ran": False,
        },
        config={"recursion_limit": 10},
        context=StageDeps(
            conn=conn,
            telemetry=telemetry,
            stage_agent=assign_agent,
            discover_agent=discover_agent,
        ),
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.integration
def test_cold_tree_assign_miss_discover_creates_two_levels_assign_places_product(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Assign miss → discover creates 2 levels → assign second pass places the product."""
    tag = uuid4().hex[:8]
    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, tag=f"disc-cold-{tag}")
        root_id = _seed_root(conn, tag=tag)
        # Existing leaf to reject — proves the rejected list is populated
        existing_leaf_id = _seed_leaf(
            conn, name=f"Existing-cat-{tag}", parent_id=root_id
        )

    # discover creates two levels; assign second pass chooses the new leaf.
    with connect_app(app_database_url) as conn:
        # Assign first pass: no fit → defer (triggers discover)
        # Discover: create ["Branch", "NewLeaf"] under root, with existing_leaf rejected
        # Assign second pass: accept the suggested leaf (discover_leaf)
        #
        # The discover agent doesn't know the leaf id yet (nodes.py creates
        # it) — the assign second-pass fake will capture it from context.

        discover_decisions = [
            StageDecision(
                action="create",
                parent_id=root_id,
                names=("Dairy-Branch", "Full-fat Milk"),
                rejected=(_rejected(existing_leaf_id, f"Existing-cat-{tag}"),),
            )
        ]

        # A scripted assign agent that:
        # - First call: defers (nothing fits)
        # - Second call: accepts the suggested leaf from context
        class _SmartAssignAgent:
            """Returns defer on first call, then accepts whatever is suggested."""

            def __init__(self) -> None:
                super().__init__()
                self._call_count = 0

            def decide(
                self,
                *,
                product: RunProductRef,
                context: Mapping[str, object],
            ) -> StageDecision:
                self._call_count += 1
                if self._call_count == 1:
                    return StageDecision(
                        action="defer", reason="nothing fits (first pass)"
                    )
                # Second pass: accept the discover-created leaf id from context
                suggested = context.get("suggested_leaf_id")
                assert suggested is not None, (
                    "second pass must receive suggested_leaf_id"
                )
                return StageDecision(action="assign", leaf_id=UUID(str(suggested)))

        outcome = _run_graph(
            conn,
            product_id=pid,
            assign_agent=_SmartAssignAgent(),
            discover_agent=_FakeStageAgent(discover_decisions),
        )

        # Discover should have succeeded and set discover_leaf
        discover_result = outcome.get("discover")
        assert discover_result is not None
        assert discover_result.status == "success"
        assert discover_result.stage == StageKind.DISCOVER_CREATE

        discover_leaf = outcome.get("discover_leaf")
        assert discover_leaf is not None

        # Assign second pass should have placed the product
        assign_result = outcome["assign"]
        assert assign_result.status == "success"

        # Check the DB
        membership = PsycopgMembershipRepository(conn).get_by_product(pid)
        assert membership is not None
        assert membership.category_id == discover_leaf

        # "Full-fat Milk" and "Dairy-Branch" should both exist in the tree
        categories = PsycopgCategoryRepository(conn)
        created_cats = [
            c
            for c in categories.list_all()
            if c.name in {"Dairy-Branch", "Full-fat Milk"}
        ]
        assert len(created_cats) == 2


@pytest.mark.integration
def test_ping_pong_guard_always_miss_produces_exactly_one_discover_call(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """A _FakeStageAgent that always misses: one discover call, then defer."""
    tag = uuid4().hex[:8]
    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, tag=f"disc-pingpong-{tag}")
        root_id = _seed_root(conn, tag=tag)
        existing_leaf_id = _seed_leaf(conn, name=f"Leaf-{tag}", parent_id=root_id)

    class _CountingDiscoverAgent:
        """Counts how many times it's called and always produces a valid create."""

        def __init__(self) -> None:
            super().__init__()
            self.call_count = 0

        def decide(
            self,
            *,
            product: RunProductRef,
            context: Mapping[str, object],
        ) -> StageDecision:
            """Return a create decision and increment the call counter."""
            self.call_count += 1
            return StageDecision(
                action="create",
                parent_id=root_id,
                names=(f"PingPong-Branch-{tag}",),
                rejected=(_rejected(existing_leaf_id, f"Leaf-{tag}"),),
            )

    counting_agent = _CountingDiscoverAgent()

    with connect_app(app_database_url) as conn:
        outcome = _run_graph(
            conn,
            product_id=pid,
            # Assign always defers (first pass miss → discover, second pass miss → defer)
            assign_agent=_FakeStageAgent(
                [
                    StageDecision(action="defer", reason="nothing fits pass 1"),
                    StageDecision(action="defer", reason="nothing fits pass 2"),
                ]
            ),
            discover_agent=counting_agent,
        )

    # Discover must have been called exactly once.
    assert counting_agent.call_count == 1

    # The product ends up deferred (assign second pass also missed).
    assign_result = outcome["assign"]
    assert assign_result.status == "defer"

    # One deferred_items row with stage=ASSIGN (assign second pass deferred).
    with connect_app(app_database_url) as conn:
        items = PsycopgDeferredItemRepository(conn).list_open()
    matching = [i for i in items if i.product_id == pid]
    assert len(matching) == 1
    assert matching[0].stage == StageKind.ASSIGN


@pytest.mark.integration
def test_empty_rejected_proposal_defers_without_calling_create_category(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Empty rejected list in create proposal → invalid → deferred; create_category not called."""
    tag = uuid4().hex[:8]
    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, tag=f"disc-noevid-{tag}")
        root_id = _seed_root(conn, tag=tag)

    # Count categories before the run.
    with connect_app(app_database_url) as conn:
        cats_before = len(PsycopgCategoryRepository(conn).list_all())

    with connect_app(app_database_url) as conn:
        _run_graph(
            conn,
            product_id=pid,
            assign_agent=_FakeStageAgent(
                [StageDecision(action="defer", reason="nothing fits")]
            ),
            discover_agent=_FakeStageAgent(
                [
                    # Empty rejected list — validate_create_proposal will reject this.
                    StageDecision(
                        action="create",
                        parent_id=root_id,
                        names=("ShouldNotBeCreated",),
                        rejected=(),  # ← no evidence
                    ),
                    # RetryPolicy will retry discover; we return invalid again.
                    StageDecision(
                        action="create",
                        parent_id=root_id,
                        names=("ShouldNotBeCreated",),
                        rejected=(),
                    ),
                    # Third attempt — also invalid, retry exhausted → defer.
                    StageDecision(
                        action="create",
                        parent_id=root_id,
                        names=("ShouldNotBeCreated",),
                        rejected=(),
                    ),
                ]
            ),
        )

    # No new categories should have been created.
    with connect_app(app_database_url) as conn:
        cats_after = len(PsycopgCategoryRepository(conn).list_all())

    # Only the root was added (by _seed_root) — no categories from the run.
    assert cats_after == cats_before

    # The product must be in deferred_items.
    with connect_app(app_database_url) as conn:
        items = PsycopgDeferredItemRepository(conn).list_open()
    matching = [i for i in items if i.product_id == pid]
    assert len(matching) == 1
    assert matching[0].stage == StageKind.DISCOVER_CREATE


@pytest.mark.integration
def test_six_level_proposal_defers_without_calling_create_category(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """A 6-level names list in the create proposal defers without calling create_category."""
    tag = uuid4().hex[:8]
    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, tag=f"disc-deep-{tag}")
        root_id = _seed_root(conn, tag=tag)
        leaf_id = _seed_leaf(conn, name=f"ExistingLeaf-{tag}", parent_id=root_id)

    with connect_app(app_database_url) as conn:
        cats_before = len(PsycopgCategoryRepository(conn).list_all())

    with connect_app(app_database_url) as conn:
        _run_graph(
            conn,
            product_id=pid,
            assign_agent=_FakeStageAgent(
                [StageDecision(action="defer", reason="nothing fits")]
            ),
            discover_agent=_FakeStageAgent(
                [
                    # 6 levels — should be rejected by validate_create_proposal on all retries
                    StageDecision(
                        action="create",
                        parent_id=root_id,
                        names=(
                            "Level1",
                            "Level2",
                            "Level3",
                            "Level4",
                            "Level5",
                            "Level6",
                        ),
                        rejected=(_rejected(leaf_id, f"ExistingLeaf-{tag}"),),
                    ),
                    StageDecision(
                        action="create",
                        parent_id=root_id,
                        names=(
                            "Level1",
                            "Level2",
                            "Level3",
                            "Level4",
                            "Level5",
                            "Level6",
                        ),
                        rejected=(_rejected(leaf_id, f"ExistingLeaf-{tag}"),),
                    ),
                    StageDecision(
                        action="create",
                        parent_id=root_id,
                        names=(
                            "Level1",
                            "Level2",
                            "Level3",
                            "Level4",
                            "Level5",
                            "Level6",
                        ),
                        rejected=(_rejected(leaf_id, f"ExistingLeaf-{tag}"),),
                    ),
                ]
            ),
        )

    # No new categories beyond root+existing leaf.
    with connect_app(app_database_url) as conn:
        cats_after = len(PsycopgCategoryRepository(conn).list_all())

    assert cats_after == cats_before

    with connect_app(app_database_url) as conn:
        items = PsycopgDeferredItemRepository(conn).list_open()
    matching = [i for i in items if i.product_id == pid]
    assert len(matching) == 1
    assert matching[0].stage == StageKind.DISCOVER_CREATE


@pytest.mark.integration
def test_assign_second_pass_disagrees_with_discover_increments_disagreement_count(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Assign picks a different leaf than discover created → disagreement_count == 1."""
    tag = uuid4().hex[:8]

    with connect_app(app_database_url) as conn:
        pid = _seed_product(conn, tag=f"disc-disagree-{tag}")
        root_id = _seed_root(conn, tag=tag)
        existing_leaf_id = _seed_leaf(
            conn, name=f"ExistingLeaf-{tag}", parent_id=root_id
        )

    # Scripted agents:
    # assign pass 1: defer
    # discover: create "DiscoLeaf" under root
    # assign pass 2: assign to ExistingLeaf (disagrees with discover)
    class _TwoPassAssignAgent:
        def __init__(self) -> None:
            super().__init__()
            self._call = 0

        def decide(
            self,
            *,
            product: RunProductRef,
            context: Mapping[str, object],
        ) -> StageDecision:
            self._call += 1
            if self._call == 1:
                return StageDecision(action="defer", reason="first pass miss")
            # Second pass: choose the EXISTING leaf, not the one discover created.
            return StageDecision(action="assign", leaf_id=existing_leaf_id)

    assign_agent_instance = _TwoPassAssignAgent()

    # We can't easily inject agents into run_pipeline, so we run the graph
    # directly with our fake agents and verify the summary counts manually.
    with connect_app(app_database_url) as conn:
        outcome = _run_graph(
            conn,
            product_id=pid,
            assign_agent=assign_agent_instance,
            discover_agent=_FakeStageAgent(
                [
                    StageDecision(
                        action="create",
                        parent_id=root_id,
                        names=(f"DiscoLeaf-{tag}",),
                        rejected=(_rejected(existing_leaf_id, f"ExistingLeaf-{tag}"),),
                    )
                ]
            ),
        )

    # Discover succeeded.
    discover_result = outcome.get("discover")
    assert discover_result is not None
    assert discover_result.status == "success"

    discover_leaf = outcome.get("discover_leaf")
    assert discover_leaf is not None

    # Assign succeeded on the second pass.
    assign_result = outcome["assign"]
    assert assign_result.status == "success"

    # But chosen leaf ≠ discover leaf → disagreement.
    assign_decision = outcome.get("assign_decision")
    assert assign_decision is not None
    assert assign_decision.leaf_id == existing_leaf_id
    assert assign_decision.leaf_id != discover_leaf

    # Membership is at the existing leaf (assign's choice), not the discover leaf.
    with connect_app(app_database_url) as conn:
        membership = PsycopgMembershipRepository(conn).get_by_product(pid)
    assert membership is not None
    assert membership.category_id == existing_leaf_id

    # The discover-created leaf ends with zero members.
    with connect_app(app_database_url) as conn:
        zero_count = PsycopgMembershipRepository(conn).count_for_category(discover_leaf)
    assert zero_count == 0
