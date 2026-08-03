"""Psycopg persistence adapters for taxonomy categories and memberships."""

from __future__ import annotations

from datetime import datetime
from typing import Any, final
from uuid import UUID

import psycopg

from pricecomp.platform.persistence.catalog_repo import PsycopgUnitOfWork, connect_app
from pricecomp.taxonomy.models import Category, Membership
from pricecomp.taxonomy.ports import (
    CategoryRepository,
    MembershipRepository,
    TaxonomyUnitOfWork,
)

# Re-export shared connection / UoW helpers used by the taxonomy runner.
__all__ = [
    "PsycopgCategoryRepository",
    "PsycopgMembershipRepository",
    "PsycopgUnitOfWork",
    "TaxonomyUnitOfWork",
    "connect_app",
]


@final
class PsycopgCategoryRepository(CategoryRepository):
    """Category repository backed by ``taxonomy_categories``."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        """Create a repository on ``conn``.

        Args:
            conn: Live psycopg connection.
        """
        super().__init__()
        self._conn = conn

    def get(self, category_id: UUID) -> Category | None:
        """Return a category by id, if present."""
        row = self._conn.execute(
            """
            SELECT id, name, parent_id, preferred_comparable_unit,
                   created_at, updated_at
            FROM taxonomy_categories
            WHERE id = %s
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            return None
        return _category_from_row(row)

    def list_all(self) -> list[Category]:
        """Return every category in the tree."""
        rows = self._conn.execute(
            """
            SELECT id, name, parent_id, preferred_comparable_unit,
                   created_at, updated_at
            FROM taxonomy_categories
            ORDER BY created_at, id
            """
        ).fetchall()
        return [_category_from_row(row) for row in rows]

    def get_root(self) -> Category | None:
        """Return the root category (parent_id IS NULL), if any."""
        row = self._conn.execute(
            """
            SELECT id, name, parent_id, preferred_comparable_unit,
                   created_at, updated_at
            FROM taxonomy_categories
            WHERE parent_id IS NULL
            """
        ).fetchone()
        if row is None:
            return None
        return _category_from_row(row)

    def insert(self, category: Category) -> Category:
        """Insert a new category row.

        Args:
            category: Category to persist.

        Returns:
            The same category instance after insert.
        """
        self._conn.execute(
            """
            INSERT INTO taxonomy_categories (
                id, name, parent_id, preferred_comparable_unit,
                created_at, updated_at
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                category.id,
                category.name,
                category.parent_id,
                category.preferred_comparable_unit,
                category.created_at,
                category.updated_at,
            ),
        )
        return category

    def update_parent(
        self,
        category_id: UUID,
        parent_id: UUID | None,
        *,
        now: datetime,
    ) -> Category:
        """Set ``parent_id`` for an existing category and bump ``updated_at``.

        Args:
            category_id: Category to move.
            parent_id: New parent (must exist unless None).
            now: Clock for ``updated_at``.

        Returns:
            The updated category.

        Raises:
            RuntimeError: If ``RETURNING`` yields no row.
        """
        row = self._conn.execute(
            """
            UPDATE taxonomy_categories
            SET parent_id = %s, updated_at = %s
            WHERE id = %s
            RETURNING id, name, parent_id, preferred_comparable_unit,
                      created_at, updated_at
            """,
            (parent_id, now, category_id),
        ).fetchone()
        if row is None:
            msg = f"Category {category_id} not found for reparent"
            raise RuntimeError(msg)
        return _category_from_row(row)


@final
class PsycopgMembershipRepository(MembershipRepository):
    """Membership repository backed by ``taxonomy_memberships``."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        """Create a repository on ``conn``.

        Args:
            conn: Live psycopg connection.
        """
        super().__init__()
        self._conn = conn

    def get_by_product(self, product_id: UUID) -> Membership | None:
        """Return the membership for a product, if any."""
        row = self._conn.execute(
            """
            SELECT product_id, category_id, assigned_at
            FROM taxonomy_memberships
            WHERE product_id = %s
            """,
            (product_id,),
        ).fetchone()
        if row is None:
            return None
        return _membership_from_row(row)

    def count_for_category(self, category_id: UUID) -> int:
        """Return how many products are assigned to ``category_id``."""
        row = self._conn.execute(
            """
            SELECT count(*) AS n
            FROM taxonomy_memberships
            WHERE category_id = %s
            """,
            (category_id,),
        ).fetchone()
        if row is None:
            return 0
        data = _as_mapping(row)
        return int(data["n"])

    def upsert(self, membership: Membership) -> Membership:
        """Insert or move membership on conflict of ``product_id``.

        Args:
            membership: Product↔leaf link to persist.

        Returns:
            The persisted membership.

        Raises:
            RuntimeError: If ``RETURNING`` yields no row.
        """
        row = self._conn.execute(
            """
            INSERT INTO taxonomy_memberships (
                product_id, category_id, assigned_at
            ) VALUES (%s, %s, %s)
            ON CONFLICT (product_id) DO UPDATE SET
                category_id = EXCLUDED.category_id,
                assigned_at = EXCLUDED.assigned_at
            RETURNING product_id, category_id, assigned_at
            """,
            (
                membership.product_id,
                membership.category_id,
                membership.assigned_at,
            ),
        ).fetchone()
        if row is None:
            msg = f"Upsert did not persist membership for {membership.product_id}"
            raise RuntimeError(msg)
        return _membership_from_row(row)


def _category_from_row(row: Any) -> Category:
    data = _as_mapping(row)
    parent = data["parent_id"]
    return Category(
        id=UUID(str(data["id"])),
        name=str(data["name"]),
        parent_id=None if parent is None else UUID(str(parent)),
        preferred_comparable_unit=_optional_str(data.get("preferred_comparable_unit")),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
    )


def _membership_from_row(row: Any) -> Membership:
    data = _as_mapping(row)
    return Membership(
        product_id=UUID(str(data["product_id"])),
        category_id=UUID(str(data["category_id"])),
        assigned_at=data.get("assigned_at"),
    )


def _as_mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    msg = f"Expected dict row, got {type(row)!r}"
    raise TypeError(msg)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
