"""Catalog domain models (framework-free)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pricecomp.catalog.identity import SourceIdentity


@dataclass(frozen=True, slots=True)
class CatalogSnapshot:
    """Immutable registration of one source CSV scrape."""

    id: UUID
    source_namespace: str
    source_observed_at: datetime
    content_checksum: str
    adapter_version: str
    source_path: str


@dataclass(frozen=True, slots=True)
class ProductObservation:
    """Imported facts for one source product row.

    Immutable value object: each ingest builds a new instance. In storage, these
    fields may change on later snapshots (unlike source identity).
    """

    identity: SourceIdentity
    name: str
    product_url: str
    shelf_price: Decimal
    currency: str = "CHF"
    # jscpd:ignore-start  # ruff: ignore[commented-out-code]
    name_de: str | None = None
    image_url: str | None = None
    price_text: str | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    original_price: Decimal | None = None
    original_unit: str | None = None
    original_unit_price: Decimal | None = None
    has_discount: bool | None = None
    discount_info: str | None = None
    source_category: str | None = None
    unified_category: str | None = None
    unified_subcategory: str | None = None
    # jscpd:ignore-end  # ruff: ignore[commented-out-code]


@dataclass(frozen=True, slots=True)
class CatalogProduct:
    """Catalog product with application ID distinct from source identity."""

    id: UUID
    identity: SourceIdentity
    name: str
    product_url: str
    shelf_price: Decimal
    currency: str
    identity_policy_version: str
    last_snapshot_id: UUID
    # jscpd:ignore-start  # ruff: ignore[commented-out-code]
    name_de: str | None = None
    image_url: str | None = None
    price_text: str | None = None
    unit: str | None = None
    unit_price: Decimal | None = None
    original_price: Decimal | None = None
    original_unit: str | None = None
    original_unit_price: Decimal | None = None
    has_discount: bool | None = None
    discount_info: str | None = None
    source_category: str | None = None
    unified_category: str | None = None
    unified_subcategory: str | None = None
    # jscpd:ignore-end  # ruff: ignore[commented-out-code]


@dataclass(frozen=True, slots=True)
class ImportSnapshotResult:
    """Outcome of registering a snapshot and upserting its products."""

    snapshot: CatalogSnapshot
    is_new_snapshot: bool
    upserted_count: int
    deferred_count: int
    collision_count: int
    deferred_urls: tuple[str, ...]
    colliding_identities: tuple[SourceIdentity, ...]
    matched_count: int = 0
    filtered_out_count: int = 0
