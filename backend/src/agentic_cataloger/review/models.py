"""Review domain models (framework-free)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from agentic_cataloger.contracts.models import StageKind


class ReasonCode(StrEnum):
    """Why an agent stage declined to produce an outcome."""

    UNKNOWN = "unknown"
    DEFER = "defer"
    LOW_CONFIDENCE = "low_confidence"


class DeferredItemStatus(StrEnum):
    """Review-item lifecycle state (single-valued for now — re-drive is 5.1)."""

    OPEN = "open"


@dataclass(frozen=True, slots=True)
class DeferredItem:
    """One product the agent won't guess about, awaiting human review."""

    id: UUID
    product_id: UUID
    stage: StageKind
    reason_code: ReasonCode
    attempt_count: int
    payload_snapshot: Mapping[str, object]
    evidence_span: str | None = None
    trace_id: str | None = None
    status: DeferredItemStatus = DeferredItemStatus.OPEN
    created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class DeferItemResult:
    """Outcome of deferring one product for human review."""

    item: DeferredItem


@dataclass(frozen=True, slots=True)
class ListDeferredItemsResult:
    """Every open deferred item, for display."""

    items: tuple[DeferredItem, ...]
