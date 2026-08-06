"""Defer and list deferred-item commands."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from dataclasses import dataclass
from uuid import UUID, uuid7

from agentic_cataloger.contracts.models import StageKind
from agentic_cataloger.review.models import (
    DeferItemResult,
    DeferredItem,
    ListDeferredItemsResult,
    ReasonCode,
)
from agentic_cataloger.review.ports import DeferredItemRepository, ReviewUnitOfWork

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class DeferItemRequest:
    """Inputs for deferring one product for human review."""

    product_id: UUID
    stage: StageKind
    reason_code: ReasonCode
    attempt_count: int
    payload_snapshot: Mapping[str, object]
    evidence_span: str | None = None
    trace_id: str | None = None


def defer_item(
    request: DeferItemRequest,
    *,
    items: DeferredItemRepository,
    uow: ReviewUnitOfWork,
) -> DeferItemResult:
    """Record that an agent stage won't guess about a product.

    Args:
        request: Product ref, stage, reason, attempt count, and payload.
        items: Deferred-item repository.
        uow: Unit of work for one transactional write.

    Returns:
        The persisted deferred item.

    Raises:
        ValueError: ``attempt_count`` is less than 1.
    """
    if request.attempt_count < 1:
        msg = "attempt_count must be >= 1"
        raise ValueError(msg)

    item = DeferredItem(
        id=uuid7(),
        product_id=request.product_id,
        stage=request.stage,
        reason_code=request.reason_code,
        attempt_count=request.attempt_count,
        payload_snapshot=request.payload_snapshot,
        evidence_span=request.evidence_span,
        trace_id=request.trace_id,
    )
    persisted = items.add(item)
    uow.commit()
    logger.info(
        "Deferred product_id=%s stage=%s reason_code=%s attempt_count=%d",
        persisted.product_id,
        persisted.stage,
        persisted.reason_code,
        persisted.attempt_count,
    )
    return DeferItemResult(item=persisted)


def list_deferred_items(*, items: DeferredItemRepository) -> ListDeferredItemsResult:
    """Return every open deferred item.

    Args:
        items: Deferred-item repository.

    Returns:
        Every deferred item with status='open'.
    """
    return ListDeferredItemsResult(items=tuple(items.list_open()))


__all__ = [
    "DeferItemRequest",
    "defer_item",
    "list_deferred_items",
]
