"""LangChain tool factories for pipeline stages, closed over a live connection.

Tools are built fresh per product from a factory rather than each opening
its own connection through a runner (unlike
``platform/taxonomy/tools.py``'s module-level tools) — see the design
discussion's resolved "where the nodes write" decision: one connection is
reused across a product's whole stage sequence.

The disjoint tool sets per stage are what make same-call create+assign
structurally impossible: ``assign_product_to_leaf`` is only ever bound in
``build_assign_tools``, never in ``build_discover_tools`` (Phase 3);
``create_category`` is the reverse.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

import psycopg
from langchain_core.tools import BaseTool, tool

from agentic_cataloger.platform.persistence.catalog_repo import PsycopgProductRepository
from agentic_cataloger.platform.persistence.taxonomy_repo import (
    PsycopgCategoryRepository,
    PsycopgMembershipRepository,
    PsycopgUnitOfWork,
)
from agentic_cataloger.taxonomy.commands import (
    AssignProductRequest,
    ListCategoryChildrenRequest,
    SearchCategoriesRequest,
    assign_product_to_leaf,
    list_category_children,
    search_categories,
)
from agentic_cataloger.taxonomy.models import Category, CategoryMatch


def _format_category_line(category: Category) -> str:
    """Format one category as a compact ``name [id]`` line.

    Args:
        category: Category to format.

    Returns:
        One-line ``name [id]`` string.
    """
    return f"{category.name} [{category.id}]"


def _format_match(match: CategoryMatch) -> str:
    """Format one search hit, with its parent, leaf status, and children.

    Args:
        match: Ranked search hit to format.

    Returns:
        Multi-line block: a header line plus one indented line per eager
        child, and a truncation note when the true child count exceeds the
        embedded children.
    """
    cat = match.category
    leaf = "leaf" if match.is_leaf else "non-leaf"
    lines = [
        f"{cat.name} [{cat.id}] parent={match.parent_name} {leaf} "
        f"score={match.score:.3f} children={match.child_count}"
    ]
    lines.extend(f"  - {_format_category_line(child)}" for child in match.children)
    if match.child_count > len(match.children):
        lines.append(f"  ... {match.child_count - len(match.children)} more, not shown")
    return "\n".join(lines)


def build_assign_tools(conn: psycopg.Connection[Any]) -> list[BaseTool]:
    """Build the assign stage's tools, all closed over ``conn``.

    ``create_category`` is deliberately absent — never reachable from the
    assign stage, mirroring ``build_discover_tools`` (Phase 3) never
    binding ``assign_product_to_leaf``.

    Args:
        conn: Live psycopg connection, reused across every tool call for
            one product's stages.

    Returns:
        ``search_categories``, ``get_category_children``, and
        ``assign_product_to_leaf`` tool objects.
    """
    categories = PsycopgCategoryRepository(conn)

    @tool("search_categories")
    def _search_categories(query: str, limit: int = 20) -> str:
        """Fuzzy-search the substitutability category tree by category name.

        Typo-tolerant and ranked by similarity, not exact/substring matching
        — close variants and misspellings still surface. Returns up to
        `limit` ranked matches (default 20, max 40); each match includes its
        parent name, leaf/non-leaf status, and up to 50 immediate children
        (useful when a match is a branch, since assignment always targets a
        leaf). Never returns the full tree or a subtree — call again with a
        different query, or use get_category_children to go deeper, instead
        of raising `limit`.

        Returns:
            One formatted block per match (name, id, parent, leaf status,
            score, and children), or "no matches".
        """
        result = search_categories(
            SearchCategoriesRequest(query=query, limit=limit),
            categories=categories,
        )
        if not result.matches:
            return "no matches"
        return "\n".join(_format_match(m) for m in result.matches)

    @tool("get_category_children")
    def _get_category_children(category_id: str | None = None, limit: int = 50) -> str:
        """List the immediate children of one category, or root categories.

        Used when `category_id` is omitted. Bounded to `limit` (max 50) —
        never a subtree or the full tree. Use this to go past the children
        already included in a search_categories match, or to browse when
        search finds nothing close enough.

        Returns:
            One "name [id]" line per child, or "no children".
        """
        parent_id = UUID(category_id) if category_id else None
        result = list_category_children(
            ListCategoryChildrenRequest(parent_id=parent_id, limit=limit),
            categories=categories,
        )
        if not result.children:
            return "no children"
        lines = [_format_category_line(c) for c in result.children]
        if result.child_count > len(result.children):
            lines.append(
                f"... {result.child_count - len(result.children)} more, not shown"
            )
        return "\n".join(lines)

    @tool("assign_product_to_leaf")
    def _assign_product_to_leaf(product_id: str, leaf_id: str) -> str:
        """Assign one product to a leaf category by id (moves on re-assign).

        Only call this once `leaf_id` is confirmed to be a LEAF (no
        children) via search_categories or get_category_children — assigning
        to a non-leaf is rejected.

        Returns:
            "assigned {product_id} to {leaf_id}", or an error line
            explaining why not (e.g. the target is not a leaf).
        """
        result = assign_product_to_leaf(
            AssignProductRequest(product_id=UUID(product_id), leaf_id=UUID(leaf_id)),
            categories=categories,
            memberships=PsycopgMembershipRepository(conn),
            products=PsycopgProductRepository(conn),
            uow=PsycopgUnitOfWork(conn),
        )
        pid = result.membership.product_id
        cid = result.membership.category_id
        return f"assigned {pid} to {cid}"

    return [_search_categories, _get_category_children, _assign_product_to_leaf]


__all__ = ["build_assign_tools"]
