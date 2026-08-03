"""Ingest filter — one criteria object for bulk, single, and filtered subsets."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from pricecomp.catalog.models import ProductObservation


def _normalize(value: str | None) -> str | None:
    """Return stripped text, or None when blank."""
    if value is None:
        return None
    stripped = value.strip()
    return stripped if stripped else None


@dataclass(frozen=True, slots=True)
class IngestFilter:
    """Filter for which products an ingest (or later pipeline run) operates on.

    Empty filter = bulk (all rows). A filter that matches one row is single —
    there is no separate mode. Category and keyword criteria AND together.
    """

    source_category: str | None = None
    keyword: str | None = None

    def __post_init__(self) -> None:
        """Normalize blank strings to None so empty CLI flags stay bulk."""
        object.__setattr__(self, "source_category", _normalize(self.source_category))
        object.__setattr__(self, "keyword", _normalize(self.keyword))

    @property
    def is_empty(self) -> bool:
        """True when no filter criteria are set (bulk)."""
        return self.source_category is None and self.keyword is None

    def matches(
        self,
        *,
        name: str,
        name_de: str | None = None,
        source_category: str | None = None,
        unified_category: str | None = None,
    ) -> bool:
        """Return True when the product fields satisfy this filter.

        ``source_category`` needle: case-insensitive substring of the retailer
        ``source_category`` field, or case-insensitive exact match of
        ``unified_category``. ``keyword``: case-insensitive substring of
        ``name`` or ``name_de``. Both criteria AND when both are set.
        """
        if self.is_empty:
            return True

        if self.source_category is not None:
            needle = self.source_category.casefold()
            retail = (source_category or "").casefold()
            unified = (unified_category or "").casefold()
            category_ok = needle in retail or needle == unified
            if not category_ok:
                return False

        if self.keyword is not None:
            needle = self.keyword.casefold()
            name_ok = needle in name.casefold()
            name_de_ok = needle in (name_de or "").casefold()
            if not (name_ok or name_de_ok):
                return False

        return True

    def matches_observation(self, observation: ProductObservation) -> bool:
        """Return True when an observation satisfies this filter."""
        return self.matches(
            name=observation.name,
            name_de=observation.name_de,
            source_category=observation.source_category,
            unified_category=observation.unified_category,
        )

    def filter_observations(
        self,
        observations: Sequence[ProductObservation],
    ) -> list[ProductObservation]:
        """Return observations that match this filter (order preserved)."""
        if self.is_empty:
            return list(observations)
        return [obs for obs in observations if self.matches_observation(obs)]


__all__ = ["IngestFilter"]
