"""Domain tests for taxonomy LangChain tool wrappers (no DB)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from agentic_cataloger.platform.taxonomy import tools as tools_module
from agentic_cataloger.taxonomy.models import (
    Category,
    CategoryMatch,
    ListCategoryChildrenResult,
    SearchCategoriesResult,
)

NOW = datetime(2026, 8, 3, 12, 0, tzinfo=UTC)


def _category(name: str) -> Category:
    return Category(
        id=uuid4(), name=name, parent_id=None, created_at=NOW, updated_at=NOW
    )


def test_search_categories_tool_reports_no_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """search_categories tool returns "no matches" when the runner finds none."""
    monkeypatch.setattr(
        tools_module,
        "run_search_categories",
        lambda *, query, limit=20: SearchCategoriesResult(matches=()),
    )

    result = tools_module.search_categories.invoke({"query": "nope"})

    assert result == "no matches"


def test_search_categories_tool_formats_matches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """search_categories tool formats one block per match, including its children."""
    parent = _category("Dairy")
    child = _category("Milk")
    match = CategoryMatch(
        category=parent,
        parent_name=None,
        is_leaf=False,
        score=0.83,
        children=(child,),
        child_count=1,
    )
    monkeypatch.setattr(
        tools_module,
        "run_search_categories",
        lambda *, query, limit=20: SearchCategoriesResult(matches=(match,)),
    )

    result = tools_module.search_categories.invoke({"query": "diary"})

    assert "Dairy" in result
    assert str(parent.id) in result
    assert "Milk" in result
    assert "non-leaf" in result


def test_get_category_children_tool_reports_no_children(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_category_children tool returns "no children" when the runner finds none."""
    monkeypatch.setattr(
        tools_module,
        "run_list_category_children",
        lambda *, parent_id=None, limit=50: ListCategoryChildrenResult(
            children=(), child_count=0
        ),
    )

    result = tools_module.get_category_children.invoke({})

    assert result == "no children"


def test_get_category_children_tool_appends_truncation_note(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A page shorter than the true child count appends a truncation line."""
    children = (_category("A"), _category("B"))
    monkeypatch.setattr(
        tools_module,
        "run_list_category_children",
        lambda *, parent_id=None, limit=50: ListCategoryChildrenResult(
            children=children, child_count=5
        ),
    )

    result = tools_module.get_category_children.invoke({})

    assert "A [" in result
    assert "B [" in result
    assert "... 3 more, not shown" in result


def test_tools_expose_name_and_description() -> None:
    """Both tools expose a name and a non-empty description for the agent."""
    assert tools_module.search_categories.name == "search_categories"
    assert tools_module.search_categories.description

    assert tools_module.get_category_children.name == "get_category_children"
    assert tools_module.get_category_children.description
