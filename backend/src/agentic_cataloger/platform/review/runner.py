"""Wire DB adapters to review application commands."""

from __future__ import annotations

import logging
import os

from agentic_cataloger.platform.persistence.review_repo import (
    PsycopgDeferredItemRepository,
    PsycopgUnitOfWork,
    connect_app,
)
from agentic_cataloger.review.commands import (
    DeferItemRequest,
    defer_item,
    list_deferred_items,
)
from agentic_cataloger.review.models import DeferItemResult, ListDeferredItemsResult

logger = logging.getLogger(__name__)


def _require_database_url(database_url: str | None) -> str:
    url = (database_url or os.environ.get("DATABASE_URL", "")).strip()
    if not url:
        msg = "DATABASE_URL must be set for review commands"
        raise RuntimeError(msg)
    return url


def run_defer_item(
    request: DeferItemRequest,
    *,
    database_url: str | None = None,
) -> DeferItemResult:
    """Record that an agent stage won't guess about a product.

    Args:
        request: Product ref, stage, reason, attempt count, and payload.
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Defer outcome with the persisted deferred item.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        return defer_item(
            request,
            items=PsycopgDeferredItemRepository(conn),
            uow=PsycopgUnitOfWork(conn),
        )


def run_list_deferred_items(
    *, database_url: str | None = None
) -> ListDeferredItemsResult:
    """List every open deferred item.

    Args:
        database_url: App DB URL; defaults to ``DATABASE_URL``.

    Returns:
        Every deferred item with status='open'.
    """
    url = _require_database_url(database_url)
    with connect_app(url) as conn:
        return list_deferred_items(items=PsycopgDeferredItemRepository(conn))
