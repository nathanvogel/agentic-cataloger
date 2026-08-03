"""Pure taxonomy tree helpers (no I/O)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from uuid import UUID

from pricecomp.taxonomy.models import Category


def parent_map(categories: Sequence[Category]) -> dict[UUID, UUID | None]:
    """Build category_id → parent_id from a category list.

    Returns:
        Mapping of each category id to its parent id (None for root).
    """
    return {category.id: category.parent_id for category in categories}


def children_map(categories: Sequence[Category]) -> dict[UUID | None, list[Category]]:
    """Group categories by parent_id (None = roots).

    Returns:
        Mapping of parent id to child category list.
    """
    by_parent: dict[UUID | None, list[Category]] = {}
    for category in categories:
        by_parent.setdefault(category.parent_id, []).append(category)
    return by_parent


def is_leaf(category_id: UUID, categories: Sequence[Category]) -> bool:
    """Return True when ``category_id`` has no children.

    Returns:
        Whether the category is a leaf.
    """
    return not any(category.parent_id == category_id for category in categories)


def would_create_cycle(
    category_id: UUID,
    new_parent_id: UUID,
    parents: Mapping[UUID, UUID | None],
) -> bool:
    """Return True if making ``new_parent_id`` parent of ``category_id`` cycles.

    Walks from the proposed parent toward the root. A cycle exists when
    ``category_id`` appears on that path (it would become its own ancestor).

    Returns:
        Whether the proposed edge would introduce a cycle.
    """
    current: UUID | None = new_parent_id
    seen: set[UUID] = set()
    while current is not None:
        if current == category_id:
            return True
        if current in seen:
            # Corrupt tree already; treat as cycle to fail closed.
            return True
        seen.add(current)
        current = parents.get(current)
    return False
