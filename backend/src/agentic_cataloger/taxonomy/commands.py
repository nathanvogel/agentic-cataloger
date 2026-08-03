"""Create, reparent, show, and assign taxonomy commands."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid7

from agentic_cataloger.taxonomy.errors import (
    CategoryNotFoundError,
    CycleError,
    NonLeafHasMembersError,
    NotLeafError,
    ProductNotFoundError,
    RootAlreadyExistsError,
    SelfParentError,
)
from agentic_cataloger.taxonomy.models import (
    AssignProductResult,
    Category,
    CreateCategoryResult,
    Membership,
    ReparentCategoryResult,
    TaxonomyTree,
)
from agentic_cataloger.taxonomy.ports import (
    CategoryRepository,
    MembershipRepository,
    ProductExistence,
    TaxonomyUnitOfWork,
)
from agentic_cataloger.taxonomy.tree import is_leaf, parent_map, would_create_cycle

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class CreateCategoryRequest:
    """Inputs for creating one category node."""

    name: str
    parent_id: UUID | None = None
    preferred_comparable_unit: str | None = None
    now: datetime | None = None


@dataclass(frozen=True, slots=True)
class ReparentCategoryRequest:
    """Inputs for moving a category under a new parent."""

    category_id: UUID
    new_parent_id: UUID
    now: datetime | None = None


@dataclass(frozen=True, slots=True)
class AssignProductRequest:
    """Inputs for assigning a product to a leaf category."""

    product_id: UUID
    leaf_id: UUID
    now: datetime | None = None


def create_category(
    request: CreateCategoryRequest,
    *,
    categories: CategoryRepository,
    memberships: MembershipRepository,
    uow: TaxonomyUnitOfWork,
) -> CreateCategoryResult:
    """Create a root or child category.

    The first create without ``parent_id`` becomes the sole root. Creating a
    child under a category that still has product memberships is rejected
    (that would demote a membered leaf to a non-leaf).

    Args:
        request: Name, optional parent, optional preferred unit.
        categories: Category repository.
        memberships: Membership repository (leaf-demotion check).
        uow: Unit of work for one transactional write.

    Returns:
        The created category.

    Raises:
        RootAlreadyExistsError: A root already exists and no parent was given.
        CategoryNotFoundError: ``parent_id`` does not exist.
        NonLeafHasMembersError: Parent has memberships (cannot gain children).
        ValueError: Category name is empty after strip.
    """
    clock = request.now if request.now is not None else datetime.now(UTC)
    name = request.name.strip()
    if not name:
        msg = "Category name must be non-empty"
        raise ValueError(msg)

    if request.parent_id is None:
        if categories.get_root() is not None:
            raise RootAlreadyExistsError(
                "A root category already exists; pass --parent <uuid>"
            )
    else:
        parent = categories.get(request.parent_id)
        if parent is None:
            raise CategoryNotFoundError(
                f"Parent category {request.parent_id} not found"
            )
        if memberships.count_for_category(request.parent_id) > 0:
            raise NonLeafHasMembersError(
                f"Category {request.parent_id} has product memberships; "
                "move those products before adding children"
            )

    category = Category(
        id=uuid7(),
        name=name,
        parent_id=request.parent_id,
        preferred_comparable_unit=request.preferred_comparable_unit,
        created_at=clock,
        updated_at=clock,
    )
    categories.insert(category)
    uow.commit()
    logger.info(
        "Created category id=%s name=%r parent_id=%s",
        category.id,
        category.name,
        category.parent_id,
    )
    return CreateCategoryResult(category=category)


def reparent_category(
    request: ReparentCategoryRequest,
    *,
    categories: CategoryRepository,
    memberships: MembershipRepository,
    uow: TaxonomyUnitOfWork,
) -> ReparentCategoryResult:
    """Move a category under a new parent.

    Rejects self-parent, cycles, missing ids, and demoting a membered leaf
    (new parent already has memberships).

    Args:
        request: Category to move and its new parent.
        categories: Category repository.
        memberships: Membership repository (leaf-demotion check).
        uow: Unit of work for one transactional write.

    Returns:
        The updated category.

    Raises:
        CategoryNotFoundError: Category or new parent missing.
        SelfParentError: ``new_parent_id`` equals ``category_id``.
        CycleError: New parent is a descendant of the category.
        NonLeafHasMembersError: New parent has memberships.
    """
    clock = request.now if request.now is not None else datetime.now(UTC)

    if request.category_id == request.new_parent_id:
        raise SelfParentError(
            f"Category {request.category_id} cannot be its own parent"
        )

    category = categories.get(request.category_id)
    if category is None:
        raise CategoryNotFoundError(f"Category {request.category_id} not found")

    new_parent = categories.get(request.new_parent_id)
    if new_parent is None:
        raise CategoryNotFoundError(
            f"Parent category {request.new_parent_id} not found"
        )

    all_categories = categories.list_all()
    if would_create_cycle(
        request.category_id,
        request.new_parent_id,
        parent_map(all_categories),
    ):
        raise CycleError(
            f"Reparenting {request.category_id} under {request.new_parent_id} "
            "would create a cycle"
        )

    if memberships.count_for_category(request.new_parent_id) > 0:
        raise NonLeafHasMembersError(
            f"Category {request.new_parent_id} has product memberships; "
            "move those products before adding children"
        )

    updated = categories.update_parent(
        request.category_id,
        request.new_parent_id,
        now=clock,
    )
    uow.commit()
    logger.info(
        "Reparented category id=%s new_parent_id=%s",
        updated.id,
        updated.parent_id,
    )
    return ReparentCategoryResult(category=updated)


def show_taxonomy(*, categories: CategoryRepository) -> TaxonomyTree:
    """Return all categories for display.

    Args:
        categories: Category repository.

    Returns:
        Unordered set of categories (CLI formats the tree).
    """
    return TaxonomyTree(categories=tuple(categories.list_all()))


def assign_product_to_leaf(
    request: AssignProductRequest,
    *,
    categories: CategoryRepository,
    memberships: MembershipRepository,
    products: ProductExistence,
    uow: TaxonomyUnitOfWork,
) -> AssignProductResult:
    """Assign a product to a leaf category (move on re-assign).

    Args:
        request: Product id and target leaf id.
        categories: Category repository.
        memberships: Membership repository.
        products: Catalog existence check.
        uow: Unit of work for one transactional write.

    Returns:
        Membership after assign; ``moved`` is True when the product already
        had a different leaf.

    Raises:
        ProductNotFoundError: Product id is not in the catalog.
        CategoryNotFoundError: Leaf id is missing.
        NotLeafError: Target has children.
    """
    clock = request.now if request.now is not None else datetime.now(UTC)

    if not products.exists(request.product_id):
        raise ProductNotFoundError(f"Product {request.product_id} not found")

    leaf = categories.get(request.leaf_id)
    if leaf is None:
        raise CategoryNotFoundError(f"Category {request.leaf_id} not found")

    all_categories = categories.list_all()
    if not is_leaf(request.leaf_id, all_categories):
        raise NotLeafError(f"Category {request.leaf_id} is not a leaf (has children)")

    existing = memberships.get_by_product(request.product_id)
    moved = existing is not None and existing.category_id != request.leaf_id

    membership = Membership(
        product_id=request.product_id,
        category_id=request.leaf_id,
        assigned_at=clock,
    )
    persisted = memberships.upsert(membership)
    uow.commit()
    logger.info(
        "Assigned product_id=%s leaf_id=%s moved=%s",
        persisted.product_id,
        persisted.category_id,
        moved,
    )
    return AssignProductResult(membership=persisted, moved=moved)


__all__ = [
    "AssignProductRequest",
    "CreateCategoryRequest",
    "ReparentCategoryRequest",
    "assign_product_to_leaf",
    "create_category",
    "reparent_category",
    "show_taxonomy",
]
