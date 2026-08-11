"""LangChain tool factories for pipeline stages, closed over an app pool.

Each tool call checks out its own connection from the pool because
``psycopg.Connection`` is not safe for concurrent use and LangGraph's
``ToolNode`` may run parallel tool calls on different threads.

Assign and discover stages bind disjoint tool sets: only assign binds
``assign_product_to_leaf``, only discover binds ``create_category``.
"""

from __future__ import annotations

from uuid import UUID

from langchain_core.tools import BaseTool, tool
from psycopg_pool import ConnectionPool

from agentic_cataloger.platform.persistence.catalog_repo import PsycopgProductRepository
from agentic_cataloger.platform.persistence.taxonomy_repo import (
    PsycopgCategoryRepository,
    PsycopgMembershipRepository,
    PsycopgUnitOfWork,
)
from agentic_cataloger.taxonomy.commands import (
    AssignProductRequest,
    CreateCategoryRequest,
    ListCategoryChildrenRequest,
    SearchCategoriesRequest,
    assign_product_to_leaf,
    create_category,
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


def build_assign_tools(pool: ConnectionPool) -> list[BaseTool]:
    """Build the assign stage's tools, each checking out from ``pool``.

    Args:
        pool: App connection pool.

    Returns:
        ``search_categories``, ``get_category_children``, and
        ``assign_product_to_leaf``.
    """

    @tool("search_categories")
    def _search_categories(query: str, limit: int = 20) -> str:
        """Fuzzy-search the substitutability category tree by category name.

        Category names in the tree are English only — pass English search
        queries (translate German product wording). Typo-tolerant and ranked
        by similarity, not exact/substring matching — close variants and
        misspellings still surface. Returns up to `limit` ranked matches
        (default 20, max 40); each match includes its parent name,
        leaf/non-leaf status, and up to 50 immediate children (useful when a
        match is a branch, since assignment always targets a leaf). Never
        returns the full tree or a subtree — prefer multiple calls in one
        turn with different queries, or use get_category_children to go
        deeper, instead of raising `limit`.

        Returns:
            One formatted block per match (name, id, parent, leaf status,
            score, and children), or "no matches".
        """
        with pool.connection() as conn:
            result = search_categories(
                SearchCategoriesRequest(query=query, limit=limit),
                categories=PsycopgCategoryRepository(conn),
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
        with pool.connection() as conn:
            result = list_category_children(
                ListCategoryChildrenRequest(parent_id=parent_id, limit=limit),
                categories=PsycopgCategoryRepository(conn),
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
        with pool.connection() as conn:
            result = assign_product_to_leaf(
                AssignProductRequest(
                    product_id=UUID(product_id), leaf_id=UUID(leaf_id)
                ),
                categories=PsycopgCategoryRepository(conn),
                memberships=PsycopgMembershipRepository(conn),
                products=PsycopgProductRepository(conn),
                uow=PsycopgUnitOfWork(conn),
            )
        pid = result.membership.product_id
        cid = result.membership.category_id
        return f"assigned {pid} to {cid}"

    return [_search_categories, _get_category_children, _assign_product_to_leaf]


def build_discover_tools(pool: ConnectionPool) -> list[BaseTool]:
    """Build the discover stage's tools, each checking out from ``pool``.

    ``create_category`` lets the model check whether a name slot is taken.
    The discover prompt asks for ``action="create"`` in structured output;
    if the model calls the tool directly, the node skips re-creating the path.

    Args:
        pool: App connection pool.

    Returns:
        ``search_categories``, ``get_category_children``, and
        ``create_category``.
    """

    @tool("search_categories")
    def _search_categories(query: str, limit: int = 20) -> str:
        """Fuzzy-search the substitutability category tree by category name.

        Category names in the tree are English only — pass English search
        queries (translate German product wording). Typo-tolerant and ranked
        by similarity, not exact/substring matching — close variants and
        misspellings still surface. Returns up to `limit` ranked matches
        (default 20, max 40); each match includes its parent name,
        leaf/non-leaf status, and up to 50 immediate children. Never returns
        the full tree or a subtree — prefer multiple calls in one turn with
        different queries, or use get_category_children to go deeper, instead
        of raising `limit`.

        Returns:
            One formatted block per match (name, id, parent, leaf status,
            score, and children), or "no matches".
        """
        with pool.connection() as conn:
            result = search_categories(
                SearchCategoriesRequest(query=query, limit=limit),
                categories=PsycopgCategoryRepository(conn),
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
        with pool.connection() as conn:
            result = list_category_children(
                ListCategoryChildrenRequest(parent_id=parent_id, limit=limit),
                categories=PsycopgCategoryRepository(conn),
            )
        if not result.children:
            return "no children"
        lines = [_format_category_line(c) for c in result.children]
        if result.child_count > len(result.children):
            lines.append(
                f"... {result.child_count - len(result.children)} more, not shown"
            )
        return "\n".join(lines)

    @tool("create_category")
    def _create_category(name: str, parent_id: str) -> str:
        """Create one new category under an existing parent.

        `name` must be English only (translate German product wording). Only
        call this to explore whether a name slot is available. To actually
        create the category path for this product, return action="create"
        with parent_id and English names in your structured response — the
        system creates the categories from your proposal, and calling this
        tool directly will result in a duplicate.

        Returns:
            "created {name} [{id}]", or an error line explaining why not
            (e.g. parent not found, parent already has product memberships).
        """
        with pool.connection() as conn:
            result = create_category(
                CreateCategoryRequest(name=name, parent_id=UUID(parent_id)),
                categories=PsycopgCategoryRepository(conn),
                memberships=PsycopgMembershipRepository(conn),
                uow=PsycopgUnitOfWork(conn),
            )
        return f"created {result.category.name} [{result.category.id}]"

    return [_search_categories, _get_category_children, _create_category]


__all__ = ["build_assign_tools", "build_discover_tools"]
