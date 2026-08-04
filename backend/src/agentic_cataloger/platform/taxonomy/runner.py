"""Wire DB adapters to taxonomy application commands."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import psycopg

from agentic_cataloger.catalog.identity import SourceIdentity
from agentic_cataloger.platform.persistence.catalog_repo import PsycopgProductRepository
from agentic_cataloger.platform.persistence.taxonomy_repo import (
    PsycopgCategoryRepository,
    PsycopgMembershipRepository,
    PsycopgUnitOfWork,
    connect_app,
)
from agentic_cataloger.taxonomy.commands import (
    AssignProductRequest,
    CreateCategoryRequest,
    ListCategoryChildrenRequest,
    ReparentCategoryRequest,
    SearchCategoriesRequest,
    assign_product_to_leaf,
    create_category,
    list_category_children,
    reparent_category,
    search_categories,
    show_taxonomy,
)
from agentic_cataloger.taxonomy.models import (
    AssignProductResult,
    Category,
    CreateCategoryResult,
    ListCategoryChildrenResult,
    ReparentCategoryResult,
    SearchCategoriesResult,
    TaxonomyTree,
)
from agentic_cataloger.taxonomy.tree import children_map

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ProductRef:
    """Product identity for assign: UUID xor source identity fields."""

    product_id: UUID | None = None
    source_namespace: str | None = None
    source_product_id: str | None = None
    source_variant_id: str | None = None


def _require_database_url(database_url: str | None) -> str:
    url = (database_url or os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        msg = "DATABASE_URL must be set for taxonomy commands"
        raise RuntimeError(msg)
    return url


def run_create_category(
    *,
    name: str,
    parent_id: UUID | None = None,
    preferred_comparable_unit: str | None = None,
    database_url: str | None = None,
) -> CreateCategoryResult:
    """Create a category in the migrated database.

    Args:
        name: Category display name.
        parent_id: Parent category UUID, or None for the root.
        preferred_comparable_unit: Optional unit string (stored, not validated).
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Create outcome with the new category.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        return create_category(
            CreateCategoryRequest(
                name=name,
                parent_id=parent_id,
                preferred_comparable_unit=preferred_comparable_unit,
            ),
            categories=PsycopgCategoryRepository(conn),
            memberships=PsycopgMembershipRepository(conn),
            uow=PsycopgUnitOfWork(conn),
        )


def run_reparent_category(
    *,
    category_id: UUID,
    new_parent_id: UUID,
    database_url: str | None = None,
) -> ReparentCategoryResult:
    """Reparent a category in the migrated database.

    Args:
        category_id: Category to move.
        new_parent_id: New parent UUID.
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Reparent outcome with the updated category.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        return reparent_category(
            ReparentCategoryRequest(
                category_id=category_id,
                new_parent_id=new_parent_id,
            ),
            categories=PsycopgCategoryRepository(conn),
            memberships=PsycopgMembershipRepository(conn),
            uow=PsycopgUnitOfWork(conn),
        )


def run_show_taxonomy(*, database_url: str | None = None) -> TaxonomyTree:
    """Load the full taxonomy tree.

    Args:
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        All categories.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        return show_taxonomy(categories=PsycopgCategoryRepository(conn))


def run_search_categories(
    *,
    query: str,
    limit: int | None = None,
    database_url: str | None = None,
) -> SearchCategoriesResult:
    """Fuzzy-search categories by name in the migrated database.

    Args:
        query: Search text.
        limit: Optional caller-supplied result cap (clamped server-side).
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Ranked search matches.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        return search_categories(
            SearchCategoriesRequest(query=query, limit=limit),
            categories=PsycopgCategoryRepository(conn),
        )


def run_list_category_children(
    *,
    parent_id: UUID | None = None,
    limit: int | None = None,
    database_url: str | None = None,
) -> ListCategoryChildrenResult:
    """List immediate children of a category in the migrated database.

    Args:
        parent_id: Parent category UUID; omit (None) for root categories.
        limit: Optional caller-supplied result cap (clamped server-side).
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        One page of children plus the true child count.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        return list_category_children(
            ListCategoryChildrenRequest(parent_id=parent_id, limit=limit),
            categories=PsycopgCategoryRepository(conn),
        )


def run_assign_product(
    *,
    product: ProductRef,
    leaf_id: UUID,
    database_url: str | None = None,
) -> AssignProductResult:
    """Assign a product to a leaf (resolve source identity when needed).

    Pass either ``product.product_id`` or namespace + source_product_id on
    ``product``, not both styles.

    Args:
        product: Catalog UUID or source identity fields.
        leaf_id: Target leaf category UUID.
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Assign outcome.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        resolved = _resolve_product_id(conn, product)
        return assign_product_to_leaf(
            AssignProductRequest(product_id=resolved, leaf_id=leaf_id),
            categories=PsycopgCategoryRepository(conn),
            memberships=PsycopgMembershipRepository(conn),
            products=PsycopgProductRepository(conn),
            uow=PsycopgUnitOfWork(conn),
        )


def format_taxonomy_tree(tree: TaxonomyTree) -> str:
    """Format a taxonomy tree for CLI stdout (indented, with ids).

    Args:
        tree: Categories to print.

    Returns:
        Multi-line tree text, or a message when empty.
    """
    if not tree.categories:
        return "(empty taxonomy)"

    by_parent = children_map(tree.categories)
    roots = by_parent.get(None, [])
    if not roots:
        return "(no root; orphaned categories present)"

    lines: list[str] = []

    def walk(category: Category, depth: int) -> None:
        unit = category.preferred_comparable_unit
        unit_part = f" unit={unit}" if unit else ""
        lines.append(f"{'  ' * depth}- {category.name} [{category.id}]{unit_part}")
        for child in by_parent.get(category.id, []):
            walk(child, depth + 1)

    for root in roots:
        walk(root, 0)
    return "\n".join(lines)


def _resolve_product_id(
    conn: psycopg.Connection[Any],
    product: ProductRef,
) -> UUID:
    """Resolve ProductRef to a catalog product UUID.

    Returns:
        Catalog product UUID.

    Raises:
        ValueError: Ambiguous or incomplete product identity flags.
        LookupError: Source identity did not resolve to a product.
    """
    has_uuid = product.product_id is not None
    has_source = (
        product.source_namespace is not None or product.source_product_id is not None
    )
    if has_uuid and has_source:
        msg = "Pass either --product-id or --namespace/--source-product-id, not both"
        raise ValueError(msg)
    if product.product_id is not None:
        return product.product_id
    if product.source_namespace is None or product.source_product_id is None:
        msg = "Assign requires --product-id or both --namespace and --source-product-id"
        raise ValueError(msg)

    identity = SourceIdentity(
        source_namespace=product.source_namespace,
        source_product_id=product.source_product_id,
        source_variant_id=product.source_variant_id,
    )
    found = PsycopgProductRepository(conn).get_by_source_identity(identity)
    if found is None:
        msg = f"No catalog product for {identity}"
        raise LookupError(msg)
    return found.id
