"""Application ports for review persistence."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from agentic_cataloger.review.models import DeferredItem


class ReviewUnitOfWork(Protocol):
    """One transactional boundary for review writes."""

    def commit(self) -> None:
        """Commit the unit of work."""
        ...

    def rollback(self) -> None:
        """Roll back the unit of work."""
        ...


class DeferredItemRepository(Protocol):
    """Persistence for review's deferred_items table."""

    def add(self, item: DeferredItem) -> DeferredItem:
        """Insert a new deferred item row."""
        ...

    def list_open(self) -> Sequence[DeferredItem]:
        """Return every deferred item with status='open'."""
        ...
