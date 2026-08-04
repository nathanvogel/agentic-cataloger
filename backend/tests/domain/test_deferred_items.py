"""Domain tests for review's defer_item/list_deferred_items commands (fakes)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import final
from uuid import UUID, uuid4

import pytest

from agentic_cataloger.contracts.models import StageKind
from agentic_cataloger.review.commands import (
    DeferItemRequest,
    defer_item,
    list_deferred_items,
)
from agentic_cataloger.review.models import DeferredItem, ReasonCode
from agentic_cataloger.review.ports import DeferredItemRepository, ReviewUnitOfWork


@final
@dataclass
class _FakeUow(ReviewUnitOfWork):
    committed: bool = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


@final
@dataclass
class _FakeDeferredItemRepository(DeferredItemRepository):
    rows: dict[UUID, DeferredItem] = field(default_factory=dict)

    def add(self, item: DeferredItem) -> DeferredItem:
        self.rows[item.id] = item
        return item

    def list_open(self) -> list[DeferredItem]:
        # The fake just returns everything it holds — the repository owns
        # the "open-only" filter, exercised for real in the Psycopg adapter.
        return list(self.rows.values())


def _request(**overrides: object) -> DeferItemRequest:
    defaults: dict[str, object] = {
        "product_id": uuid4(),
        "stage": StageKind.ASSIGN,
        "reason_code": ReasonCode.LOW_CONFIDENCE,
        "attempt_count": 1,
        "payload_snapshot": {"note": "example"},
    }
    defaults.update(overrides)
    return DeferItemRequest(**defaults)  # type: ignore[arg-type]


def test_defer_item_mints_id_commits_and_returns_item() -> None:
    """defer_item mints a UUID, commits the unit of work, and returns the item."""
    items = _FakeDeferredItemRepository()
    uow = _FakeUow()

    result = defer_item(_request(), items=items, uow=uow)

    assert isinstance(result.item.id, UUID)
    assert uow.committed is True
    assert items.rows[result.item.id] == result.item
    assert result.item.reason_code == ReasonCode.LOW_CONFIDENCE
    assert result.item.stage == StageKind.ASSIGN


def test_defer_item_rejects_attempt_count_below_one() -> None:
    """attempt_count < 1 raises ValueError."""
    items = _FakeDeferredItemRepository()
    uow = _FakeUow()

    with pytest.raises(ValueError, match="attempt_count"):
        defer_item(_request(attempt_count=0), items=items, uow=uow)


def test_list_deferred_items_returns_only_stored_rows() -> None:
    """list_deferred_items returns exactly what the repo holds."""
    items = _FakeDeferredItemRepository()
    uow = _FakeUow()
    first = defer_item(_request(), items=items, uow=uow).item
    second = defer_item(_request(), items=items, uow=uow).item

    result = list_deferred_items(items=items)

    assert {item.id for item in result.items} == {first.id, second.id}
