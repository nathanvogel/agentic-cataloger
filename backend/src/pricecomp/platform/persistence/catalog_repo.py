"""Psycopg persistence adapters for catalog snapshots and products."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, cast, final
from uuid import UUID

import psycopg
from psycopg.rows import DictRow, dict_row

from pricecomp.catalog.identity import SourceIdentity
from pricecomp.catalog.models import CatalogProduct, CatalogSnapshot, ProductObservation
from pricecomp.catalog.ports import (
    CatalogUnitOfWork,
    ProductRepository,
    SnapshotRepository,
)
from pricecomp.taxonomy.ports import ProductExistence


@final
class PsycopgUnitOfWork(CatalogUnitOfWork):
    """Thin Unit of Work over a psycopg connection."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        """Bind to an open connection (caller owns connect/close).

        Args:
            conn: Live psycopg connection with autocommit disabled.
        """
        super().__init__()
        self._conn = conn

    def commit(self) -> None:
        """Commit the current transaction."""
        self._conn.commit()

    def rollback(self) -> None:
        """Roll back the current transaction."""
        self._conn.rollback()


@final
class PsycopgSnapshotRepository(SnapshotRepository):
    """Snapshot repository backed by ``catalog_snapshots``."""

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        """Create a repository on ``conn``.

        Args:
            conn: Live psycopg connection.
        """
        super().__init__()
        self._conn = conn

    def get_by_checksum_and_adapter(
        self,
        *,
        content_checksum: str,
        adapter_version: str,
    ) -> CatalogSnapshot | None:
        """Return an existing snapshot for checksum + adapter version, if any."""
        row = self._conn.execute(
            """
            SELECT id, source_namespace, source_observed_at, content_checksum,
                   adapter_version, source_path
            FROM catalog_snapshots
            WHERE content_checksum = %s AND adapter_version = %s
            """,
            (content_checksum, adapter_version),
        ).fetchone()
        if row is None:
            return None
        return _snapshot_from_row(row)

    def insert(self, snapshot: CatalogSnapshot) -> CatalogSnapshot:
        """Insert a new snapshot row.

        Args:
            snapshot: Snapshot to persist.

        Returns:
            The same snapshot instance after insert.
        """
        self._conn.execute(
            """
            INSERT INTO catalog_snapshots (
                id, source_namespace, source_observed_at, content_checksum,
                adapter_version, source_path
            ) VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                snapshot.id,
                snapshot.source_namespace,
                snapshot.source_observed_at,
                snapshot.content_checksum,
                snapshot.adapter_version,
                snapshot.source_path,
            ),
        )
        return snapshot


@final
class PsycopgProductRepository(ProductRepository, ProductExistence):
    """Product repository backed by ``catalog_products``.

    Implements the full ``ProductRepository`` surface plus the slim
    ``ProductExistence`` check used by taxonomy assign.
    """

    def __init__(self, conn: psycopg.Connection[Any]) -> None:
        """Create a repository on ``conn``.

        Args:
            conn: Live psycopg connection.
        """
        super().__init__()
        self._conn = conn

    def exists(self, product_id: UUID) -> bool:
        """Return True when ``product_id`` is a catalog product."""
        row = self._conn.execute(
            "SELECT 1 FROM catalog_products WHERE id = %s",
            (product_id,),
        ).fetchone()
        return row is not None

    def get_by_source_identity(self, identity: SourceIdentity) -> CatalogProduct | None:
        """Return the product for a source identity, if present."""
        row = self._conn.execute(
            """
            SELECT *
            FROM catalog_products
            WHERE source_namespace = %s
              AND source_product_id = %s
              AND source_variant_id IS NOT DISTINCT FROM %s
            """,
            (
                identity.source_namespace,
                identity.source_product_id,
                identity.source_variant_id,
            ),
        ).fetchone()
        if row is None:
            return None
        return _product_from_row(row)

    def get_identity_policy_version(self, source_namespace: str) -> str | None:
        """Return the identity policy version already used in a namespace, if any."""
        row = self._conn.execute(
            """
            SELECT identity_policy_version
            FROM catalog_products
            WHERE source_namespace = %s
            LIMIT 1
            """,
            (source_namespace,),
        ).fetchone()
        if row is None:
            return None
        return str(row["identity_policy_version"])

    def upsert_observation(
        self,
        *,
        product_id: UUID,
        observation: ProductObservation,
        snapshot_id: UUID,
        identity_policy_version: str,
        now: datetime,
    ) -> CatalogProduct:
        """Insert or update mutable observations; never touch enrichment state.

        Args:
            product_id: Application UUIDv7 for inserts (ignored on conflict).
            observation: Mutable imported facts.
            snapshot_id: Snapshot that produced this observation.
            identity_policy_version: Versioned URL→ID policy.
            now: Clock for created_at / updated_at.

        Returns:
            The persisted catalog product.

        Raises:
            RuntimeError: If ``RETURNING`` yields no row.
        """
        identity = observation.identity
        row = self._conn.execute(
            """
            INSERT INTO catalog_products (
                id, source_namespace, source_product_id, source_variant_id,
                name, name_de, product_url, image_url,
                shelf_price, currency, price_text, unit, unit_price,
                original_price, original_unit, original_unit_price,
                has_discount, discount_info, source_category,
                unified_category, unified_subcategory,
                identity_policy_version, last_snapshot_id,
                created_at, updated_at
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s
            )
            ON CONFLICT ON CONSTRAINT catalog_products_source_identity_uq
            DO UPDATE SET
                name = EXCLUDED.name,
                name_de = EXCLUDED.name_de,
                product_url = EXCLUDED.product_url,
                image_url = EXCLUDED.image_url,
                shelf_price = EXCLUDED.shelf_price,
                currency = EXCLUDED.currency,
                price_text = EXCLUDED.price_text,
                unit = EXCLUDED.unit,
                unit_price = EXCLUDED.unit_price,
                original_price = EXCLUDED.original_price,
                original_unit = EXCLUDED.original_unit,
                original_unit_price = EXCLUDED.original_unit_price,
                has_discount = EXCLUDED.has_discount,
                discount_info = EXCLUDED.discount_info,
                source_category = EXCLUDED.source_category,
                unified_category = EXCLUDED.unified_category,
                unified_subcategory = EXCLUDED.unified_subcategory,
                identity_policy_version = EXCLUDED.identity_policy_version,
                last_snapshot_id = EXCLUDED.last_snapshot_id,
                updated_at = EXCLUDED.updated_at
            RETURNING *
            """,
            (
                product_id,
                identity.source_namespace,
                identity.source_product_id,
                identity.source_variant_id,
                observation.name,
                observation.name_de,
                observation.product_url,
                observation.image_url,
                observation.shelf_price,
                observation.currency,
                observation.price_text,
                observation.unit,
                observation.unit_price,
                observation.original_price,
                observation.original_unit,
                observation.original_unit_price,
                observation.has_discount,
                observation.discount_info,
                observation.source_category,
                observation.unified_category,
                observation.unified_subcategory,
                identity_policy_version,
                snapshot_id,
                now,
                now,
            ),
        ).fetchone()
        if row is None:
            msg = f"Upsert did not persist product for {identity}"
            raise RuntimeError(msg)
        return _product_from_row(row)


def connect_app(database_url: str) -> psycopg.Connection[DictRow]:
    """Open an app-role connection with dict rows and autocommit off.

    Args:
        database_url: ``postgresql://…`` URL for ``pricecomp_app``.

    Returns:
        Open psycopg connection.
    """
    # psycopg stubs default Connection to TupleRow; cast after dict_row.
    return cast(
        psycopg.Connection[DictRow],
        psycopg.connect(
            database_url,
            row_factory=cast(Any, dict_row),
            autocommit=False,
        ),
    )


def _snapshot_from_row(row: Any) -> CatalogSnapshot:
    data = _as_mapping(row)
    return CatalogSnapshot(
        id=UUID(str(data["id"])),
        source_namespace=str(data["source_namespace"]),
        source_observed_at=data["source_observed_at"],
        content_checksum=str(data["content_checksum"]),
        adapter_version=str(data["adapter_version"]),
        source_path=str(data["source_path"]),
    )


def _product_from_row(row: Any) -> CatalogProduct:
    data = _as_mapping(row)
    return CatalogProduct(
        id=UUID(str(data["id"])),
        identity=SourceIdentity(
            source_namespace=str(data["source_namespace"]),
            source_product_id=str(data["source_product_id"]),
            source_variant_id=(
                None
                if data["source_variant_id"] is None
                else str(data["source_variant_id"])
            ),
        ),
        name=str(data["name"]),
        name_de=_optional_str(data.get("name_de")),
        product_url=str(data["product_url"]),
        image_url=_optional_str(data.get("image_url")),
        shelf_price=Decimal(str(data["shelf_price"])),
        currency=str(data["currency"]),
        price_text=_optional_str(data.get("price_text")),
        unit=_optional_str(data.get("unit")),
        unit_price=_optional_decimal(data.get("unit_price")),
        original_price=_optional_decimal(data.get("original_price")),
        original_unit=_optional_str(data.get("original_unit")),
        original_unit_price=_optional_decimal(data.get("original_unit_price")),
        has_discount=data.get("has_discount"),
        discount_info=_optional_str(data.get("discount_info")),
        source_category=_optional_str(data.get("source_category")),
        unified_category=_optional_str(data.get("unified_category")),
        unified_subcategory=_optional_str(data.get("unified_subcategory")),
        identity_policy_version=str(data["identity_policy_version"]),
        last_snapshot_id=UUID(str(data["last_snapshot_id"])),
    )


def _as_mapping(row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return row
    # tuple row from tests without dict_row — not expected in production paths
    msg = f"Expected dict row, got {type(row)!r}"
    raise TypeError(msg)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return Decimal(str(value))
