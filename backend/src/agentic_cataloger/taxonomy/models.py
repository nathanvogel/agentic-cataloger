"""Taxonomy domain models (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class Category:
    """One node in the substitutability tree."""

    id: UUID
    name: str
    parent_id: UUID | None
    preferred_comparable_unit: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class Membership:
    """Product assigned to exactly one leaf category."""

    product_id: UUID
    category_id: UUID
    assigned_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class TaxonomyTree:
    """All categories in the tree (unordered; callers derive structure)."""

    categories: tuple[Category, ...]


@dataclass(frozen=True, slots=True)
class CreateCategoryResult:
    """Outcome of creating one category."""

    category: Category


@dataclass(frozen=True, slots=True)
class ReparentCategoryResult:
    """Outcome of moving a category under a new parent."""

    category: Category


@dataclass(frozen=True, slots=True)
class AssignProductResult:
    """Outcome of assigning a product to a leaf."""

    membership: Membership
    moved: bool


CHILDREN_LIMIT = 50


@dataclass(frozen=True, slots=True)
class CategoryMatch:
    """One ranked category search hit, with eager immediate children.

    Not a persisted row: ``category`` plus context computed at query time.
    ``children`` is capped at ``CHILDREN_LIMIT``; ``child_count`` is the true
    count, which may exceed ``len(children)``.
    """

    category: Category
    parent_name: str | None
    is_leaf: bool
    score: float
    children: tuple[Category, ...]
    child_count: int


@dataclass(frozen=True, slots=True)
class SearchCategoriesResult:
    """Ranked category matches for a fuzzy-search query."""

    matches: tuple[CategoryMatch, ...]


@dataclass(frozen=True, slots=True)
class ListCategoryChildrenResult:
    """One page of a category's immediate children, plus the true count."""

    children: tuple[Category, ...]
    child_count: int
