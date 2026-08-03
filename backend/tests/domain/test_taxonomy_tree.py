"""Domain tests for taxonomy tree + leaf membership (fakes)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import final
from uuid import UUID, uuid4

import pytest

from pricecomp.taxonomy.commands import (
    AssignProductRequest,
    CreateCategoryRequest,
    ReparentCategoryRequest,
    assign_product_to_leaf,
    create_category,
    reparent_category,
    show_taxonomy,
)
from pricecomp.taxonomy.errors import (
    CycleError,
    NonLeafHasMembersError,
    NotLeafError,
    RootAlreadyExistsError,
    SelfParentError,
)
from pricecomp.taxonomy.models import Category, Membership
from pricecomp.taxonomy.ports import (
    CategoryRepository,
    MembershipRepository,
    ProductExistence,
    TaxonomyUnitOfWork,
)
from pricecomp.taxonomy.tree import is_leaf, would_create_cycle


@final
@dataclass
class _FakeUow(TaxonomyUnitOfWork):
    committed: bool = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


@final
@dataclass
class _FakeCategories(CategoryRepository):
    rows: dict[UUID, Category] = field(default_factory=dict)

    def get(self, category_id: UUID) -> Category | None:
        return self.rows.get(category_id)

    def list_all(self) -> list[Category]:
        return list(self.rows.values())

    def get_root(self) -> Category | None:
        for category in self.rows.values():
            if category.parent_id is None:
                return category
        return None

    def insert(self, category: Category) -> Category:
        self.rows[category.id] = category
        return category

    def update_parent(
        self,
        category_id: UUID,
        parent_id: UUID | None,
        *,
        now: datetime,
    ) -> Category:
        existing = self.rows[category_id]
        updated = Category(
            id=existing.id,
            name=existing.name,
            parent_id=parent_id,
            preferred_comparable_unit=existing.preferred_comparable_unit,
            created_at=existing.created_at,
            updated_at=now,
        )
        self.rows[category_id] = updated
        return updated


@final
@dataclass
class _FakeMemberships(MembershipRepository):
    by_product: dict[UUID, Membership] = field(default_factory=dict)

    def get_by_product(self, product_id: UUID) -> Membership | None:
        return self.by_product.get(product_id)

    def count_for_category(self, category_id: UUID) -> int:
        return sum(1 for m in self.by_product.values() if m.category_id == category_id)

    def upsert(self, membership: Membership) -> Membership:
        self.by_product[membership.product_id] = membership
        return membership


@final
@dataclass
class _FakeProducts(ProductExistence):
    ids: set[UUID] = field(default_factory=set)

    def exists(self, product_id: UUID) -> bool:
        return product_id in self.ids


NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


def _create(
    categories: _FakeCategories,
    memberships: _FakeMemberships,
    uow: _FakeUow,
    *,
    name: str,
    parent_id: UUID | None = None,
    unit: str | None = None,
) -> Category:
    return create_category(
        CreateCategoryRequest(
            name=name,
            parent_id=parent_id,
            preferred_comparable_unit=unit,
            now=NOW,
        ),
        categories=categories,
        memberships=memberships,
        uow=uow,
    ).category


def test_would_create_cycle_detects_descendant_as_parent() -> None:
    """Reparenting a node under its own descendant is a cycle."""
    root = uuid4()
    child = uuid4()
    grandchild = uuid4()
    parents = {root: None, child: root, grandchild: child}
    assert would_create_cycle(child, grandchild, parents) is True
    assert would_create_cycle(grandchild, root, parents) is False


def test_is_leaf_when_no_children() -> None:
    """A node with no children is a leaf."""
    root_id = uuid4()
    leaf_id = uuid4()
    categories = [
        Category(id=root_id, name="root", parent_id=None),
        Category(id=leaf_id, name="leaf", parent_id=root_id),
    ]
    assert is_leaf(leaf_id, categories) is True
    assert is_leaf(root_id, categories) is False


def test_create_root_then_child_and_show() -> None:
    """Creating a root and child yields a two-node tree."""
    categories = _FakeCategories()
    memberships = _FakeMemberships()
    uow = _FakeUow()

    root = _create(categories, memberships, uow, name="Dairy", unit="L")
    child = _create(categories, memberships, uow, name="Cow milk", parent_id=root.id)

    tree = show_taxonomy(categories=categories)
    assert {c.id for c in tree.categories} == {root.id, child.id}
    assert child.parent_id == root.id
    assert root.preferred_comparable_unit == "L"


def test_second_root_rejected() -> None:
    """Only one root is allowed."""
    categories = _FakeCategories()
    memberships = _FakeMemberships()
    uow = _FakeUow()
    _create(categories, memberships, uow, name="Root")

    with pytest.raises(RootAlreadyExistsError):
        _create(categories, memberships, uow, name="Other root")


def test_reparent_that_would_cycle_rejected() -> None:
    """Moving a parent under its descendant fails with CycleError."""
    categories = _FakeCategories()
    memberships = _FakeMemberships()
    uow = _FakeUow()
    root = _create(categories, memberships, uow, name="Root")
    child = _create(categories, memberships, uow, name="Child", parent_id=root.id)
    grandchild = _create(categories, memberships, uow, name="Grand", parent_id=child.id)

    with pytest.raises(CycleError):
        reparent_category(
            ReparentCategoryRequest(
                category_id=child.id,
                new_parent_id=grandchild.id,
                now=NOW,
            ),
            categories=categories,
            memberships=memberships,
            uow=uow,
        )


def test_self_parent_rejected() -> None:
    """A category cannot be its own parent."""
    categories = _FakeCategories()
    memberships = _FakeMemberships()
    uow = _FakeUow()
    root = _create(categories, memberships, uow, name="Root")

    with pytest.raises(SelfParentError):
        reparent_category(
            ReparentCategoryRequest(
                category_id=root.id,
                new_parent_id=root.id,
                now=NOW,
            ),
            categories=categories,
            memberships=memberships,
            uow=uow,
        )


def test_assign_to_non_leaf_rejected() -> None:
    """Assign requires a leaf target."""
    categories = _FakeCategories()
    memberships = _FakeMemberships()
    products = _FakeProducts()
    uow = _FakeUow()
    root = _create(categories, memberships, uow, name="Root")
    _create(categories, memberships, uow, name="Leaf", parent_id=root.id)
    product_id = uuid4()
    products.ids.add(product_id)

    with pytest.raises(NotLeafError):
        assign_product_to_leaf(
            AssignProductRequest(product_id=product_id, leaf_id=root.id, now=NOW),
            categories=categories,
            memberships=memberships,
            products=products,
            uow=uow,
        )


def test_assign_moves_on_reassign() -> None:
    """Second assign for the same product moves membership to the new leaf."""
    categories = _FakeCategories()
    memberships = _FakeMemberships()
    products = _FakeProducts()
    uow = _FakeUow()
    root = _create(categories, memberships, uow, name="Root")
    leaf_a = _create(categories, memberships, uow, name="A", parent_id=root.id)
    leaf_b = _create(categories, memberships, uow, name="B", parent_id=root.id)
    product_id = uuid4()
    products.ids.add(product_id)

    first = assign_product_to_leaf(
        AssignProductRequest(product_id=product_id, leaf_id=leaf_a.id, now=NOW),
        categories=categories,
        memberships=memberships,
        products=products,
        uow=uow,
    )
    assert first.moved is False
    assert first.membership.category_id == leaf_a.id

    second = assign_product_to_leaf(
        AssignProductRequest(product_id=product_id, leaf_id=leaf_b.id, now=NOW),
        categories=categories,
        memberships=memberships,
        products=products,
        uow=uow,
    )
    assert second.moved is True
    assert second.membership.category_id == leaf_b.id
    assert len(memberships.by_product) == 1


def test_create_child_under_membered_leaf_rejected() -> None:
    """Cannot demote a leaf that still has product memberships."""
    categories = _FakeCategories()
    memberships = _FakeMemberships()
    products = _FakeProducts()
    uow = _FakeUow()
    root = _create(categories, memberships, uow, name="Root")
    leaf = _create(categories, memberships, uow, name="Leaf", parent_id=root.id)
    product_id = uuid4()
    products.ids.add(product_id)
    assign_product_to_leaf(
        AssignProductRequest(product_id=product_id, leaf_id=leaf.id, now=NOW),
        categories=categories,
        memberships=memberships,
        products=products,
        uow=uow,
    )

    with pytest.raises(NonLeafHasMembersError):
        _create(categories, memberships, uow, name="Child", parent_id=leaf.id)


def test_reparent_onto_membered_leaf_rejected() -> None:
    """Cannot reparent under a node that still has memberships."""
    categories = _FakeCategories()
    memberships = _FakeMemberships()
    products = _FakeProducts()
    uow = _FakeUow()
    root = _create(categories, memberships, uow, name="Root")
    leaf_a = _create(categories, memberships, uow, name="A", parent_id=root.id)
    leaf_b = _create(categories, memberships, uow, name="B", parent_id=root.id)
    product_id = uuid4()
    products.ids.add(product_id)
    assign_product_to_leaf(
        AssignProductRequest(product_id=product_id, leaf_id=leaf_a.id, now=NOW),
        categories=categories,
        memberships=memberships,
        products=products,
        uow=uow,
    )

    with pytest.raises(NonLeafHasMembersError):
        reparent_category(
            ReparentCategoryRequest(
                category_id=leaf_b.id,
                new_parent_id=leaf_a.id,
                now=NOW,
            ),
            categories=categories,
            memberships=memberships,
            uow=uow,
        )
