"""Psycopg persistence adapters for taxonomy categories and memberships."""

from __future__ import annotations

from datetime import datetime
from typing import Any, final
from uuid import UUID

import psycopg

from agentic_cataloger.platform.persistence.catalog_repo import (
    PsycopgUnitOfWork,
    connect_app,
)
from agentic_cataloger.taxonomy.models import (
    CHILDREN_LIMIT,
    Category,
    CategoryMatch,
    Membership,
)
from agentic_cataloger.taxonomy.ports import (
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

    def search(self, query: str, *, limit: int) -> list[CategoryMatch]:
        """Return categories ranked by name similarity to `query`, capped at `limit`."""
        # Postgres's default pg_trgm.similarity_threshold (0.3) is tuned for
        # longer text and misses common single-transposition typos on short
        # category names (e.g. "diary" vs "Dairy" scores 0.2). SET doesn't
        # accept bind parameters, so this stays a literal.
        self._conn.execute("SET LOCAL pg_trgm.similarity_threshold = 0.15")
        rows = self._conn.execute(
            """
            SELECT c.id, c.name, c.parent_id, c.preferred_comparable_unit,
                   c.created_at, c.updated_at,
                   p.name AS parent_name,
                   NOT EXISTS (
                       SELECT 1 FROM taxonomy_categories x WHERE x.parent_id = c.id
                   ) AS is_leaf,
                   similarity(c.name, %(query)s) AS score,
                   COALESCE(kids.children, '[]'::jsonb) AS children,
                   COALESCE(kids.child_count, 0) AS child_count
            FROM taxonomy_categories c
            LEFT JOIN taxonomy_categories p ON p.id = c.parent_id
            LEFT JOIN LATERAL (
                SELECT
                    jsonb_agg(
                        jsonb_build_object('id', ch.id, 'name', ch.name)
                        ORDER BY ch.name
                    ) FILTER (WHERE ch.rn <= %(children_limit)s) AS children,
                    count(*) AS child_count
                FROM (
                    SELECT id, name, row_number() OVER (ORDER BY name) AS rn
                    FROM taxonomy_categories
                    WHERE parent_id = c.id
                ) ch
            ) kids ON true
            WHERE c.name %% %(query)s
            ORDER BY score DESC, c.name
            LIMIT %(limit)s
            """,
            {"query": query, "children_limit": CHILDREN_LIMIT, "limit": limit},
        ).fetchall()
        return [_category_match_from_row(row) for row in rows]

    def children(
        self, parent_id: UUID | None, *, limit: int
    ) -> tuple[list[Category], int]:
        """Return immediate children of `parent_id` (None = root categories).

        Capped at `limit`, plus the true child count.
        """
        rows = self._conn.execute(
            """
            SELECT id, name, parent_id, preferred_comparable_unit,
                   created_at, updated_at
            FROM taxonomy_categories
            WHERE parent_id IS NOT DISTINCT FROM %s
            ORDER BY name
            LIMIT %s
            """,
            (parent_id, limit),
        ).fetchall()
        count_row = self._conn.execute(
            """
            SELECT count(*) AS n
            FROM taxonomy_categories
            WHERE parent_id IS NOT DISTINCT FROM %s
            """,
            (parent_id,),
        ).fetchone()
        child_count = int(_as_mapping(count_row)["n"]) if count_row is not None else 0
        return [_category_from_row(row) for row in rows], child_count


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


def _category_match_from_row(row: Any) -> CategoryMatch:
    data = _as_mapping(row)
    category = _category_from_row(row)
    children_raw = data.get("children") or []
    children = tuple(
        Category(
            id=UUID(str(child["id"])),
            name=str(child["name"]),
            parent_id=category.id,
        )
        for child in children_raw
    )
    return CategoryMatch(
        category=category,
        parent_name=_optional_str(data.get("parent_name")),
        is_leaf=bool(data["is_leaf"]),
        score=float(data["score"]),
        children=children,
        child_count=int(data["child_count"]),
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
