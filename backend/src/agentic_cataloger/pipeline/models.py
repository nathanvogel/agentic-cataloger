"""Pipeline domain models (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass
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


__all__ = ["RunProductRef", "SelectRunProductsResult"]
