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

    Required evidence for a create proposal (roadmap 2.6) — checked by
    ``validate_create_proposal`` on ``CreateDecision``.
    """

    category_id: UUID
    name: str


@dataclass(frozen=True, slots=True)
class AssignDecision:
    """Assign stage chose an existing leaf category."""

    leaf_id: UUID
    reason: str | None = None

    @property
    def action(self) -> Literal["assign"]:
        """Discriminator for routing and telemetry."""
        return "assign"


@dataclass(frozen=True, slots=True)
class DeferDecision:
    """Stage declined to place the product (model-initiated or converted miss)."""

    reason: str | None = None

    @property
    def action(self) -> Literal["defer"]:
        """Discriminator for routing and telemetry."""
        return "defer"


@dataclass(frozen=True, slots=True)
class CreateDecision:
    """Discover stage proposed a new category path under ``parent_id``."""

    parent_id: UUID
    names: tuple[str, ...]
    rejected: tuple[RejectedCandidate, ...]
    reason: str | None = None

    @property
    def action(self) -> Literal["create"]:
        """Discriminator for routing and telemetry."""
        return "create"


StageDecision = AssignDecision | DeferDecision | CreateDecision


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
    "AssignDecision",
    "CreateDecision",
    "DeferDecision",
    "RejectedCandidate",
    "RunProductRef",
    "RunSummary",
    "SelectRunProductsResult",
    "StageDecision",
]
