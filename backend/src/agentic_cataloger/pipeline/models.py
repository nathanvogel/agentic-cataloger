"""Pipeline domain models (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RunProductRef:
    """One catalog product selected for a pipeline run.

    Carries just enough for filter matching and later stage payloads — not
    the full ``CatalogProduct`` shape.
    """

    product_id: UUID
    name: str
    name_de: str | None
    source_category: str | None
    unified_category: str | None


@dataclass(frozen=True, slots=True)
class SelectRunProductsResult:
    """Outcome of selecting the products a pipeline run will operate on."""

    products: tuple[RunProductRef, ...]


@dataclass(frozen=True, slots=True)
class RejectedCandidate:
    """One existing category the discover stage considered and rejected.

    Required evidence for a create proposal (roadmap 2.6) — unused until
    ``StageDecision`` grows a ``create`` payload and ``validate_create_proposal``
    checks it (Phase 3), but the shape is fixed now alongside ``StageDecision``.
    """

    category_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class StageDecision:
    """One stage's decision, converted from the LLM's structured output.

    The domain shape the platform's ``response_format`` schema converts
    into — never constructed directly from raw LLM output outside
    ``platform/pipeline/agent.py``.

    ``action="create"`` and its payload (parent/names/rejected candidates)
    belong to the discover stage; the assign stage only ever produces
    ``"assign"`` (with ``leaf_id`` set) or ``"defer"``.
    """

    action: Literal["assign", "create", "defer"]
    leaf_id: UUID | None = None
    reason: str | None = None
    # Phase 3 create payload — only populated when action="create"
    parent_id: UUID | None = None
    names: tuple[str, ...] = ()
    rejected: tuple[RejectedCandidate, ...] = ()


@dataclass(frozen=True, slots=True)
class RunSummary:
    """Counts printed at the end of a pipeline run.

    ``created_count``/``disagreement_count`` stay 0 until Phase 3 adds the
    discover/create stage — nothing creates categories yet.
    """

    product_count: int
    deferred_count: int
    created_count: int = 0
    disagreement_count: int = 0


__all__ = [
    "RejectedCandidate",
    "RunProductRef",
    "RunSummary",
    "SelectRunProductsResult",
    "StageDecision",
]
