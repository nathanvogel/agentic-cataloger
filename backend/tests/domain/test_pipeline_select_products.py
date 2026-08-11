"""Domain tests for pipeline.commands.select_run_products (fakes)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import final
from uuid import uuid4

from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.catalog.models import CatalogProductRef
from agentic_cataloger.catalog.ports import CatalogProductQuery
from agentic_cataloger.pipeline.commands import (
    SelectRunProductsRequest,
    select_run_products,
)


@final
@dataclass
class _FakeCatalogProducts(CatalogProductQuery):
    """In-memory CatalogProductQuery fake recording its last call args."""

    rows: list[CatalogProductRef] = field(default_factory=list)
    last_ingest_filter: IngestFilter | None = None
    last_unassigned_only: bool | None = None
    last_limit: int | None = None

    def list_refs(
        self,
        *,
        ingest_filter: IngestFilter,
        unassigned_only: bool,
        limit: int | None,
    ) -> list[CatalogProductRef]:
        self.last_ingest_filter = ingest_filter
        self.last_unassigned_only = unassigned_only
        self.last_limit = limit
        return list(self.rows)[:limit] if limit is not None else list(self.rows)


def _ref(name: str = "Milk") -> CatalogProductRef:
    return CatalogProductRef(
        product_id=uuid4(),
        name=name,
        name_de=None,
        source_category=None,
        unified_category=None,
    )


def test_select_run_products_passes_through_filter_and_limit() -> None:
    """select_run_products forwards the request's filter, limit, and flag as-is."""
    ingest_filter = IngestFilter(source_category="Milchprodukte")
    products = _FakeCatalogProducts(rows=[_ref("Milk"), _ref("Cheese")])

    result = select_run_products(
        SelectRunProductsRequest(
            ingest_filter=ingest_filter, unassigned_only=False, limit=1
        ),
        products=products,
    )

    assert products.last_ingest_filter is ingest_filter
    assert products.last_unassigned_only is False
    assert products.last_limit == 1
    assert len(result.products) == 1
    assert result.products[0].name == "Milk"


def test_select_run_products_defaults_to_unassigned_only() -> None:
    """The default request excludes already-assigned products and has no cap."""
    products = _FakeCatalogProducts(rows=[_ref()])

    select_run_products(
        SelectRunProductsRequest(ingest_filter=IngestFilter()),
        products=products,
    )

    assert products.last_unassigned_only is True
    assert products.last_limit is None


def test_select_run_products_empty_filter_returns_all() -> None:
    """An empty IngestFilter selects everything the repository returns."""
    products = _FakeCatalogProducts(rows=[_ref("A"), _ref("B"), _ref("C")])

    result = select_run_products(
        SelectRunProductsRequest(ingest_filter=IngestFilter()),
        products=products,
    )

    assert [p.name for p in result.products] == ["A", "B", "C"]
