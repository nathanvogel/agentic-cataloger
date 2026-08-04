"""Unit tests for IngestFilter matching rules."""

from __future__ import annotations

from decimal import Decimal

from agentic_cataloger.catalog.identity import SourceIdentity
from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.catalog.models import ProductObservation


def _obs(
    *,
    name: str = "Milk",
    name_de: str | None = None,
    source_category: str | None = None,
    unified_category: str | None = None,
    product_id: str = "1",
) -> ProductObservation:
    return ProductObservation(
        identity=SourceIdentity("migros-ch", product_id),
        name=name,
        product_url=f"https://www.migros.ch/de/product/{product_id}",
        shelf_price=Decimal("1.50"),
        name_de=name_de,
        source_category=source_category,
        unified_category=unified_category,
    )


def test_empty_filter_matches_all() -> None:
    """Empty filter is bulk — every observation matches."""
    ingest_filter = IngestFilter()
    assert ingest_filter.is_empty is True
    assert ingest_filter.matches(name="Anything", source_category=None) is True
    assert len(ingest_filter.filter_observations([_obs(), _obs(product_id="2")])) == 2


def test_blank_strings_normalize_to_empty() -> None:
    """Whitespace-only CLI flags collapse to bulk."""
    assert IngestFilter(source_category="  ", keyword="").is_empty is True


def test_source_category_substring_case_insensitive() -> None:
    """Retailer category matches as a case-insensitive substring."""
    ingest_filter = IngestFilter(source_category="milchprodukte")
    assert (
        ingest_filter.matches(
            name="Milch",
            source_category="Milchprodukte, Eier & frische Fertiggerichte",
        )
        is True
    )
    assert ingest_filter.matches(name="Brot", source_category="Backwaren") is False


def test_unified_category_exact_case_insensitive() -> None:
    """Unified category matches by exact (case-insensitive) equality only."""
    ingest_filter = IngestFilter(source_category="dairy")
    assert ingest_filter.matches(name="Milk", unified_category="dairy") is True
    assert ingest_filter.matches(name="Milk", unified_category="Dairy") is True
    assert ingest_filter.matches(name="Milk", unified_category="dairy_extra") is False
    assert (
        ingest_filter.matches(
            name="Milk",
            source_category="something else",
            unified_category="meat",
        )
        is False
    )


def test_keyword_matches_name_or_name_de() -> None:
    """Keyword is a case-insensitive substring of name or name_de."""
    ingest_filter = IngestFilter(keyword="litschi")
    assert ingest_filter.matches(name="Litschis Offenverkauf") is True
    assert ingest_filter.matches(name="Fruit", name_de="Litschis") is True
    assert ingest_filter.matches(name="Apple", name_de="Apfel") is False


def test_category_and_keyword_and_together() -> None:
    """Both criteria must hold when both are set."""
    ingest_filter = IngestFilter(source_category="Obst", keyword="litschi")
    assert (
        ingest_filter.matches(
            name="Litschis",
            source_category="Obst",
        )
        is True
    )
    assert ingest_filter.matches(name="Apfel", source_category="Obst") is False
    assert ingest_filter.matches(name="Litschis", source_category="Backwaren") is False


def test_filter_observations_preserves_order() -> None:
    """filter_observations keeps input order of matches."""
    ingest_filter = IngestFilter(source_category="dairy")
    rows = [
        _obs(product_id="1", unified_category="meat"),
        _obs(product_id="2", unified_category="dairy"),
        _obs(product_id="3", unified_category="dairy"),
        _obs(product_id="4", unified_category="bakery"),
    ]
    matched = ingest_filter.filter_observations(rows)
    assert [o.identity.source_product_id for o in matched] == ["2", "3"]


def test_no_match_returns_empty() -> None:
    """A needle that hits nothing yields an empty list."""
    ingest_filter = IngestFilter(source_category="zzzz-missing")
    assert ingest_filter.filter_observations([_obs(source_category="Obst")]) == []
