"""LangChain tools exposing taxonomy category reads to an LLM agent.

The only module in the taxonomy vertical allowed to import ``langchain`` —
``test_taxonomy_boundaries.py`` forbids that import inside ``taxonomy/``
itself. Wraps ``platform/taxonomy/runner.py`` and formats compact strings
(not JSON-schema-shaped objects), since a plain string return becomes
``ToolMessage.content`` directly with no schema-repetition tax.
"""

from __future__ import annotations

from uuid import UUID

from langchain_core.tools import tool

from agentic_cataloger.platform.taxonomy.runner import (
    run_list_category_children,
    run_search_categories,
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


@tool
def search_categories(query: str, limit: int = 20) -> str:
    """Fuzzy-search the substitutability category tree by category name.

    Typo-tolerant and ranked by similarity, not exact/substring matching —
    close variants and misspellings still surface. Returns up to `limit`
    ranked matches (default 20, max 40); each match includes its parent
    name, leaf/non-leaf status, and up to 50 immediate children (useful
    when a match is a branch, since assignment always targets a leaf).
    Never returns the full tree or a subtree — prefer multiple calls in one
    turn with different queries, or use get_category_children to go deeper,
    instead of raising `limit`.

    Returns:
        One formatted block per match (name, id, parent, leaf status,
        score, and children), or "no matches".
    """
    result = run_search_categories(query=query, limit=limit)
    if not result.matches:
        return "no matches"
    return "\n".join(_format_match(m) for m in result.matches)


@tool
def get_category_children(category_id: str | None = None, limit: int = 50) -> str:
    """List the immediate children of one category, or root categories.

    Used when `category_id` is omitted. Bounded to `limit` (max 50) —
    never a subtree or the full tree. Use this to go past the children
    already included in a search_categories match, or to browse when
    search finds nothing close enough.

    Returns:
        One "name [id]" line per child, or "no children".
    """
    parent_id = UUID(category_id) if category_id else None
    result = run_list_category_children(parent_id=parent_id, limit=limit)
    if not result.children:
        return "no children"
    lines = [_format_category_line(c) for c in result.children]
    if result.child_count > len(result.children):
        lines.append(f"... {result.child_count - len(result.children)} more, not shown")
    return "\n".join(lines)
