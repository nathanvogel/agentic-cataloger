"""Domain tests for Phase 3 additions: ensure_root_category, validate_create_proposal.

Uses in-memory fakes only — no DB, no LLM.  Covers:
- ensure_root_category skips the write when a root already exists.
- ensure_root_category creates "All products" when no root is present.
- validate_create_proposal rejects an empty rejected list.
- validate_create_proposal rejects a path longer than 5 levels.
- validate_create_proposal rejects an empty names list.
- validate_create_proposal accepts a valid single-level proposal.
- validate_create_proposal accepts a valid two-level proposal.
- validate_create_proposal accepts a valid five-level proposal.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Sequence
from uuid import UUID, uuid4

import pytest

from agentic_cataloger.pipeline.commands import (
    ensure_root_category,
    validate_create_proposal,
)
from agentic_cataloger.pipeline.models import RejectedCandidate, StageDecision
from agentic_cataloger.taxonomy.models import Category, CategoryMatch, Membership

# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeUow:
    """Minimal unit of work that tracks commit calls."""

    def __init__(self) -> None:
        super().__init__()
        self.committed = False

    def commit(self) -> None:
        """Record commit."""
        self.committed = True

    def rollback(self) -> None:
        """No-op rollback."""


class _FakeMembershipRepository:
    """Membership repository that always returns zero members."""

    @staticmethod
    def get_by_product(product_id: UUID) -> Membership | None:
        """Return None — no memberships."""
        return None

    @staticmethod
    def count_for_category(category_id: UUID) -> int:
        """Return 0 — no members."""
        return 0

    @staticmethod
    def upsert(membership: Membership) -> Membership:
        """No-op upsert."""
        return membership


def _make_root() -> Category:
    now = datetime.now(UTC)
    return Category(
        id=uuid4(),
        name="All products",
        parent_id=None,
        preferred_comparable_unit=None,
        created_at=now,
        updated_at=now,
    )


class _FakeCategoryRepository:
    """In-memory category repository driven by a supplied root (or None)."""

    def __init__(self, root: Category | None = None) -> None:
        super().__init__()
        self._root = root
        self._inserted: list[Category] = []

    def get(self, category_id: UUID) -> Category | None:
        """Return a category by id if it was inserted."""
        all_cats = ([self._root] if self._root else []) + self._inserted
        return next((c for c in all_cats if c.id == category_id), None)

    def list_all(self) -> Sequence[Category]:
        """Return all categories."""
        return ([self._root] if self._root else []) + self._inserted

    def get_root(self) -> Category | None:
        """Return the root category."""
        return self._root

    def insert(self, category: Category) -> Category:
        """Store and return the inserted category."""
        if category.parent_id is None:
            self._root = category
        self._inserted.append(category)
        return category

    def update_parent(
        self,
        category_id: UUID,
        parent_id: UUID | None,
        *,
        now: datetime,
    ) -> Category:
        """Raise — not used in ensure_root tests."""
        raise NotImplementedError

    def search(self, query: str, *, limit: int) -> Sequence[CategoryMatch]:
        """Raise — not used in ensure_root tests."""
        raise NotImplementedError

    def children(
        self, parent_id: UUID | None, *, limit: int
    ) -> tuple[Sequence[Category], int]:
        """Return children of parent_id."""
        kids = [c for c in self._inserted if c.parent_id == parent_id]
        return kids[:limit], len(kids)


# ---------------------------------------------------------------------------
# ensure_root_category tests
# ---------------------------------------------------------------------------


def test_ensure_root_skipped_when_root_exists() -> None:
    """ensure_root_category is a no-op when a root already exists."""
    root = _make_root()
    cats = _FakeCategoryRepository(root=root)
    uow = _FakeUow()

    ensure_root_category(
        categories=cats,
        memberships=_FakeMembershipRepository(),
        uow=uow,
    )

    assert not uow.committed
    assert cats.get_root() is root
    assert cats._inserted == []


def test_ensure_root_creates_all_products_when_no_root() -> None:
    """ensure_root_category creates 'All products' when no root is present."""
    cats = _FakeCategoryRepository(root=None)
    uow = _FakeUow()

    ensure_root_category(
        categories=cats,
        memberships=_FakeMembershipRepository(),
        uow=uow,
    )

    assert uow.committed
    root = cats.get_root()
    assert root is not None
    assert root.name == "All products"
    assert root.parent_id is None


# ---------------------------------------------------------------------------
# validate_create_proposal tests
# ---------------------------------------------------------------------------


def _rejected(n: int = 1) -> tuple[RejectedCandidate, ...]:
    return tuple(
        RejectedCandidate(category_id=uuid4(), name=f"rejected-cat-{i}")
        for i in range(n)
    )


def test_validate_create_proposal_rejects_empty_rejected() -> None:
    """A create decision with no rejected candidates raises ValueError."""
    decision = StageDecision(
        action="create",
        parent_id=uuid4(),
        names=("Dairy",),
        rejected=(),
    )

    with pytest.raises(ValueError, match="rejected candidate"):
        validate_create_proposal(decision)


def test_validate_create_proposal_rejects_empty_names() -> None:
    """A create decision with no names raises ValueError."""
    decision = StageDecision(
        action="create",
        parent_id=uuid4(),
        names=(),
        rejected=_rejected(1),
    )

    with pytest.raises(ValueError, match="name"):
        validate_create_proposal(decision)


def test_validate_create_proposal_rejects_path_longer_than_5() -> None:
    """A create path deeper than 5 levels raises ValueError."""
    decision = StageDecision(
        action="create",
        parent_id=uuid4(),
        names=("Level1", "Level2", "Level3", "Level4", "Level5", "Level6"),
        rejected=_rejected(1),
    )

    with pytest.raises(ValueError, match="5 levels"):
        validate_create_proposal(decision)


def test_validate_create_proposal_accepts_single_level() -> None:
    """A valid single-level proposal passes without raising."""
    decision = StageDecision(
        action="create",
        parent_id=uuid4(),
        names=("New Leaf",),
        rejected=_rejected(1),
    )

    validate_create_proposal(decision)  # should not raise


def test_validate_create_proposal_accepts_two_levels() -> None:
    """A valid two-level proposal passes without raising."""
    decision = StageDecision(
        action="create",
        parent_id=uuid4(),
        names=("New Branch", "New Leaf"),
        rejected=_rejected(2),
    )

    validate_create_proposal(decision)  # should not raise


def test_validate_create_proposal_accepts_five_levels() -> None:
    """A valid five-level proposal passes without raising."""
    decision = StageDecision(
        action="create",
        parent_id=uuid4(),
        names=(
            "New Branch",
            "New Sub-branch",
            "New Sub-sub-branch",
            "New Sub-sub-sub-branch",
            "New Leaf",
        ),
        rejected=_rejected(2),
    )

    validate_create_proposal(decision)  # should not raise
