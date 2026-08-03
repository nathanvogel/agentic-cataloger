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
