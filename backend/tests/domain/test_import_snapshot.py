"""Unit tests for import_snapshot command (in-memory ports)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import final
from uuid import UUID

import pytest

from agentic_cataloger.catalog.commands import ImportSnapshotRequest, import_snapshot
from agentic_cataloger.catalog.errors import IdentityPolicyConflictError
from agentic_cataloger.catalog.identity import IDENTITY_POLICY_VERSION, SourceIdentity
from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.catalog.models import (
    CatalogProduct,
    CatalogSnapshot,
    ProductObservation,
)
from agentic_cataloger.catalog.ports import (
    CatalogUnitOfWork,
    ProductRepository,
    SnapshotRepository,
)


@final
@dataclass
class _FakeUow(CatalogUnitOfWork):
    committed: bool = False

    def commit(self) -> None:
        self.committed = True

    def rollback(self) -> None:
        self.committed = False


@final
@dataclass
class _FakeSnapshots(SnapshotRepository):
    rows: dict[tuple[str, str], CatalogSnapshot] = field(default_factory=dict)

    def get_by_checksum_and_adapter(
        self,
        *,
        content_checksum: str,
        adapter_version: str,
    ) -> CatalogSnapshot | None:
        return self.rows.get((content_checksum, adapter_version))

    def insert(self, snapshot: CatalogSnapshot) -> CatalogSnapshot:
        key = (snapshot.content_checksum, snapshot.adapter_version)
        self.rows[key] = snapshot
        return snapshot


@final
@dataclass
class _FakeProducts(ProductRepository):
    by_identity: dict[SourceIdentity, CatalogProduct] = field(default_factory=dict)
    policy_by_namespace: dict[str, str] = field(default_factory=dict)

    def get_by_source_identity(self, identity: SourceIdentity) -> CatalogProduct | None:
        return self.by_identity.get(identity)

    def get_identity_policy_version(self, source_namespace: str) -> str | None:
        return self.policy_by_namespace.get(source_namespace)

    def upsert_observation(
        self,
        *,
        product_id: UUID,
        observation: ProductObservation,
        snapshot_id: UUID,
        identity_policy_version: str,
        now: datetime,
    ) -> CatalogProduct:
        existing = self.by_identity.get(observation.identity)
        # Match Postgres: ON CONFLICT keeps the existing row id.
        product = CatalogProduct(
            id=existing.id if existing is not None else product_id,
            identity=observation.identity,
            name=observation.name,
            product_url=observation.product_url,
            shelf_price=observation.shelf_price,
            currency=observation.currency,
            identity_policy_version=identity_policy_version,
            last_snapshot_id=snapshot_id,
            name_de=observation.name_de,
        )
        self.by_identity[observation.identity] = product
        self.policy_by_namespace[observation.identity.source_namespace] = (
            identity_policy_version
        )
        return product


def _observation(
    *,
    product_id: str = "100",
    variant: str | None = None,
    name: str = "Milk",
    url: str = "https://www.migros.ch/de/product/100",
    name_de: str | None = None,
    source_category: str | None = None,
    unified_category: str | None = None,
) -> ProductObservation:
    return ProductObservation(
        identity=SourceIdentity("migros-ch", product_id, variant),
        name=name,
        product_url=url,
        shelf_price=Decimal("1.50"),
        name_de=name_de,
        source_category=source_category,
        unified_category=unified_category,
    )


def _run(
    *,
    checksum: str,
    observations: list[ProductObservation],
    deferred: list[tuple[str, str]] | None = None,
    snapshots: _FakeSnapshots | None = None,
    products: _FakeProducts | None = None,
    uow: _FakeUow | None = None,
    observed_at: datetime | None = None,
    identity_policy_version: str = IDENTITY_POLICY_VERSION,
    source_path: str = "a.csv",
    ingest_filter: IngestFilter | None = None,
):
    snaps = snapshots if snapshots is not None else _FakeSnapshots()
    prods = products if products is not None else _FakeProducts()
    unit = uow if uow is not None else _FakeUow()
    return (
        import_snapshot(
            ImportSnapshotRequest(
                source_namespace="migros-ch",
                source_observed_at=observed_at
                or datetime(2025, 12, 30, 15, 22, tzinfo=UTC),
                content_checksum=checksum,
                source_path=source_path,
                observations=observations,
                deferred=deferred or [],
                identity_policy_version=identity_policy_version,
                ingest_filter=(
                    ingest_filter if ingest_filter is not None else IngestFilter()
                ),
            ),
            snapshots=snaps,
            products=prods,
            uow=unit,
        ),
        snaps,
        prods,
        unit,
    )


def test_import_registers_snapshot_and_upserts() -> None:
    """Happy path creates a snapshot and one product inside one UoW commit."""
    result, _snaps, _products, uow = _run(
        checksum="abc",
        observations=[_observation()],
        observed_at=datetime(2025, 12, 30, 15, 22),
        source_path="migros-ch-products/2025/12/30-15:22.csv",
    )
    assert result.is_new_snapshot is True
    assert result.upserted_count == 1
    assert uow.committed is True
    assert result.snapshot.source_observed_at.tzinfo is UTC


def test_same_checksum_reuses_snapshot() -> None:
    """Same checksum + adapter version resolves to the existing snapshot."""
    snapshots = _FakeSnapshots()
    products = _FakeProducts()
    first, _, _, _ = _run(
        checksum="abc",
        observations=[_observation()],
        snapshots=snapshots,
        products=products,
    )
    second, _, _, _ = _run(
        checksum="abc",
        observations=[_observation(name="Milk 2%", url="https://example/product/100")],
        snapshots=snapshots,
        products=products,
    )
    assert second.is_new_snapshot is False
    assert second.snapshot.id == first.snapshot.id
    assert len(snapshots.rows) == 1
    stored = products.by_identity[SourceIdentity("migros-ch", "100")]
    assert stored.name == "Milk 2%"


def test_reimport_keeps_same_product_id_after_name_change() -> None:
    """Name/URL changes update observations; source identity stays the product key."""
    snapshots = _FakeSnapshots()
    products = _FakeProducts()
    _run(
        checksum="c1",
        observations=[_observation(name="Old", url="https://old/product/100")],
        snapshots=snapshots,
        products=products,
    )
    before = products.by_identity[SourceIdentity("migros-ch", "100")]
    _run(
        checksum="c2",
        observations=[_observation(name="New", url="https://new/product/100")],
        snapshots=snapshots,
        products=products,
        observed_at=datetime(2025, 12, 31, 11, 35, tzinfo=UTC),
        source_path="b.csv",
    )
    after = products.by_identity[SourceIdentity("migros-ch", "100")]
    assert after.id == before.id
    assert after.name == "New"
    assert after.product_url == "https://new/product/100"


def test_deferred_produces_no_product() -> None:
    """Deferred records are counted and create no catalog product."""
    result, _, products, _ = _run(
        checksum="d1",
        observations=[],
        deferred=[("https://bad", "no id")],
    )
    assert result.deferred_count == 1
    assert result.upserted_count == 0
    assert products.by_identity == {}


def test_intra_snapshot_collision_skipped() -> None:
    """Two rows with the same source identity in one snapshot are not upserted."""
    result, _, products, _ = _run(
        checksum="x1",
        observations=[
            _observation(name="A"),
            _observation(name="B", url="https://www.migros.ch/de/product/100?x=1"),
        ],
    )
    assert result.collision_count == 1
    assert result.upserted_count == 0
    assert products.by_identity == {}


def test_identity_policy_conflict_refused() -> None:
    """Namespace policy change without an alias map is refused."""
    products = _FakeProducts()
    products.policy_by_namespace["migros-ch"] = "old-policy@0"
    with pytest.raises(IdentityPolicyConflictError):
        _run(
            checksum="p1",
            observations=[_observation()],
            products=products,
        )


def test_null_variant_collides_as_identity() -> None:
    """Null variant is part of the identity key (NULLS NOT DISTINCT semantics)."""
    products = _FakeProducts()
    _run(
        checksum="n1",
        observations=[_observation(variant=None, name="One")],
        products=products,
    )
    _run(
        checksum="n2",
        observations=[_observation(variant=None, name="Two")],
        products=products,
        source_path="b.csv",
    )
    assert len(products.by_identity) == 1
    assert products.by_identity[SourceIdentity("migros-ch", "100")].name == "Two"


def test_application_id_is_uuid_distinct_from_source() -> None:
    """Product carries a UUIDv7 application identity distinct from source ids."""
    _, _, products, _ = _run(checksum="u1", observations=[_observation()])
    product = next(iter(products.by_identity.values()))
    assert isinstance(product.id, UUID)
    assert str(product.id) != product.identity.source_product_id
    assert product.id.version == 7


def test_empty_filter_upserts_all_unique() -> None:
    """Empty filter keeps bulk behavior — every unique observation upserts."""
    result, _, products, _ = _run(
        checksum="bulk-1",
        observations=[
            _observation(product_id="1", name="A", url="https://x/product/1"),
            _observation(product_id="2", name="B", url="https://x/product/2"),
        ],
    )
    assert result.matched_count == 2
    assert result.filtered_out_count == 0
    assert result.upserted_count == 2
    assert len(products.by_identity) == 2


def test_category_filter_upserts_subset_only() -> None:
    """Source-category filter upserts matching rows through the same path."""
    result, _, products, _ = _run(
        checksum="filt-1",
        observations=[
            _observation(
                product_id="1",
                name="Milk",
                url="https://x/product/1",
                source_category="Milchprodukte, Eier",
            ),
            _observation(
                product_id="2",
                name="Bread",
                url="https://x/product/2",
                source_category="Backwaren",
            ),
            _observation(
                product_id="3",
                name="Yogurt",
                url="https://x/product/3",
                unified_category="dairy",
            ),
        ],
        ingest_filter=IngestFilter(source_category="Milchprodukte"),
    )
    assert result.matched_count == 1
    assert result.filtered_out_count == 2
    assert result.upserted_count == 1
    assert SourceIdentity("migros-ch", "1") in products.by_identity
    assert SourceIdentity("migros-ch", "2") not in products.by_identity
    assert SourceIdentity("migros-ch", "3") not in products.by_identity


def test_filter_of_one_uses_same_import_path() -> None:
    """A filter matching exactly one product is still import_snapshot."""
    result, _, products, _ = _run(
        checksum="single-1",
        observations=[
            _observation(
                product_id="1",
                name="Litschis",
                url="https://x/product/1",
                source_category="Obst",
            ),
            _observation(
                product_id="2",
                name="Apfel",
                url="https://x/product/2",
                source_category="Obst",
            ),
        ],
        ingest_filter=IngestFilter(keyword="litschi"),
    )
    assert result.upserted_count == 1
    assert result.matched_count == 1
    assert list(products.by_identity) == [SourceIdentity("migros-ch", "1")]


def test_filtered_import_leaves_non_matching_products_untouched() -> None:
    """Seeded products outside the filter are not updated or removed."""
    snapshots = _FakeSnapshots()
    products = _FakeProducts()
    _run(
        checksum="seed-1",
        observations=[
            _observation(
                product_id="keep",
                name="Keep Me",
                url="https://x/product/keep",
                source_category="Backwaren",
            ),
        ],
        snapshots=snapshots,
        products=products,
    )
    before = products.by_identity[SourceIdentity("migros-ch", "keep")]
    result, _, _, _ = _run(
        checksum="seed-2",
        observations=[
            _observation(
                product_id="keep",
                name="Should Not Overwrite",
                url="https://x/product/keep",
                source_category="Backwaren",
            ),
            _observation(
                product_id="new",
                name="Milk",
                url="https://x/product/new",
                source_category="Milchprodukte",
            ),
        ],
        snapshots=snapshots,
        products=products,
        ingest_filter=IngestFilter(source_category="Milchprodukte"),
        source_path="b.csv",
    )
    assert result.upserted_count == 1
    after = products.by_identity[SourceIdentity("migros-ch", "keep")]
    assert after.id == before.id
    assert after.name == "Keep Me"
    assert SourceIdentity("migros-ch", "new") in products.by_identity


def test_zero_match_filter_still_registers_snapshot() -> None:
    """Non-matching filter upserts nothing but still registers the snapshot."""
    result, snaps, products, uow = _run(
        checksum="zero-1",
        observations=[
            _observation(source_category="Obst"),
        ],
        ingest_filter=IngestFilter(source_category="zzzz"),
    )
    assert result.is_new_snapshot is True
    assert result.matched_count == 0
    assert result.filtered_out_count == 1
    assert result.upserted_count == 0
    assert products.by_identity == {}
    assert len(snaps.rows) == 1
    assert uow.committed is True
