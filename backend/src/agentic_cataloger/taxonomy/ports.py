"""Application ports for taxonomy persistence."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol
from uuid import UUID

from agentic_cataloger.taxonomy.models import Category, Membership


class TaxonomyUnitOfWork(Protocol):
    """One transactional boundary for taxonomy writes."""

    def commit(self) -> None:
        """Commit the unit of work."""
        ...

    def rollback(self) -> None:
        """Roll back the unit of work."""
        ...


class CategoryRepository(Protocol):
    """Persistence for substitutability categories."""

    def get(self, category_id: UUID) -> Category | None:
        """Return a category by id, if present."""
        ...

    def list_all(self) -> Sequence[Category]:
        """Return every category in the tree."""
        ...

    def get_root(self) -> Category | None:
        """Return the root category (parent_id IS NULL), if any."""
        ...

    def insert(self, category: Category) -> Category:
        """Insert a new category row."""
        ...

    def update_parent(
        self,
        category_id: UUID,
        parent_id: UUID | None,
        *,
        now: datetime,
    ) -> Category:
        """Set ``parent_id`` for an existing category and bump ``updated_at``."""
        ...


class MembershipRepository(Protocol):
    """Persistence for product↔leaf membership (one leaf per product)."""

    def get_by_product(self, product_id: UUID) -> Membership | None:
        """Return the membership for a product, if any."""
        ...

    def count_for_category(self, category_id: UUID) -> int:
        """Return how many products are assigned to ``category_id``."""
        ...

    def upsert(self, membership: Membership) -> Membership:
        """Insert or move membership on conflict of ``product_id``."""
        ...


class ProductExistence(Protocol):
    """Minimal catalog lookup used by assign (FK target must exist)."""

    def exists(self, product_id: UUID) -> bool:
        """Return True when ``product_id`` is a catalog product."""
        ...
