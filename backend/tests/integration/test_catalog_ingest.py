"""Integration tests for catalog snapshot registration and product ingest (1.4)."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import psycopg
import pytest
from tests.conftest import REPO_ROOT

from pricecomp.catalog.commands import (
    CSV_ADAPTER_VERSION,
    ImportSnapshotRequest,
    import_snapshot,
)
from pricecomp.catalog.identity import IDENTITY_POLICY_VERSION, SourceIdentity
from pricecomp.catalog.models import ProductObservation
from pricecomp.platform.ingest.csv_source import (
    find_latest_csv,
    parse_csv_snapshot,
    parse_snapshot_timestamp,
)
from pricecomp.platform.ingest.runner import run_ingest
from pricecomp.platform.persistence.catalog_repo import (
    PsycopgProductRepository,
    PsycopgSnapshotRepository,
    PsycopgUnitOfWork,
    connect_app,
)


def _import(
    conn: psycopg.Connection[Any],
    *,
    source_namespace: str,
    source_observed_at: datetime,
    content_checksum: str,
    source_path: str,
    observations: list[ProductObservation] | None = None,
    deferred: list[tuple[str, str]] | None = None,
):
    return import_snapshot(
        ImportSnapshotRequest(
            source_namespace=source_namespace,
            source_observed_at=source_observed_at,
            content_checksum=content_checksum,
            source_path=source_path,
            observations=observations or [],
            deferred=deferred or [],
        ),
        snapshots=PsycopgSnapshotRepository(conn),
        products=PsycopgProductRepository(conn),
        uow=PsycopgUnitOfWork(conn),
    )


@pytest.mark.integration
def test_snapshot_registration_fields(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Registration stores UTC observed time, checksum, adapter version, UUIDv7."""
    with connect_app(app_database_url) as conn:
        result = _import(
            conn,
            source_namespace="migros-ch",
            source_observed_at=datetime(2025, 12, 30, 15, 22),
            content_checksum="checksum-1",
            source_path="migros-ch-products/2025/12/30-15:22.csv",
        )
    snap = result.snapshot
    assert snap.id.version == 7
    assert snap.source_observed_at == datetime(2025, 12, 30, 15, 22, tzinfo=UTC)
    assert snap.content_checksum == "checksum-1"
    assert snap.adapter_version == CSV_ADAPTER_VERSION


@pytest.mark.integration
def test_snapshot_identifying_fields_immutable_at_db(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Identifying-field UPDATE/DELETE is rejected at the database level."""
    with connect_app(app_database_url) as conn:
        result = _import(
            conn,
            source_namespace="migros-ch",
            source_observed_at=datetime(2025, 12, 30, 15, 22, tzinfo=UTC),
            content_checksum="immutable-1",
            source_path="a.csv",
        )
        snap_id = result.snapshot.id

    with psycopg.connect(app_database_url) as conn:
        with pytest.raises(psycopg.Error):
            conn.execute(
                "UPDATE catalog_snapshots SET content_checksum = %s WHERE id = %s",
                ("tampered", snap_id),
            )
            conn.commit()
        conn.rollback()
        with pytest.raises(psycopg.Error):
            conn.execute("DELETE FROM catalog_snapshots WHERE id = %s", (snap_id,))
            conn.commit()
        conn.rollback()
        row = conn.execute(
            "SELECT content_checksum FROM catalog_snapshots WHERE id = %s",
            (snap_id,),
        ).fetchone()
        assert row is not None
        assert row[0] == "immutable-1"


@pytest.mark.integration
def test_same_checksum_adapter_dedupes(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Same checksum + adapter version registered twice yields one snapshot row."""
    with connect_app(app_database_url) as conn:
        first = _import(
            conn,
            source_namespace="lidl-ch",
            source_observed_at=datetime(2025, 12, 31, 11, 35, tzinfo=UTC),
            content_checksum="same",
            source_path="a.csv",
        )
        second = _import(
            conn,
            source_namespace="lidl-ch",
            source_observed_at=datetime(2025, 12, 31, 11, 35, tzinfo=UTC),
            content_checksum="same",
            source_path="a.csv",
        )
    assert first.snapshot.id == second.snapshot.id
    assert second.is_new_snapshot is False
    with psycopg.connect(app_database_url) as conn:
        count = conn.execute(
            "SELECT count(*) AS n FROM catalog_snapshots WHERE content_checksum = %s",
            ("same",),
        ).fetchone()
        assert count is not None
        assert count[0] == 1


@pytest.mark.integration
def test_product_source_identity_unique_nulls_not_distinct(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Null variant collides under UNIQUE NULLS NOT DISTINCT."""
    identity = SourceIdentity("coop-ch", "6495669", None)
    obs = ProductObservation(
        identity=identity,
        name="Bananas",
        product_url="https://www.coop.ch/p/6495669",
        shelf_price=Decimal("3.20"),
        unified_category="vegetables",
    )
    with connect_app(app_database_url) as conn:
        _import(
            conn,
            source_namespace="coop-ch",
            source_observed_at=datetime(2026, 2, 25, 21, 46, tzinfo=UTC),
            content_checksum="coop-1",
            source_path="coop.csv",
            observations=[obs],
        )
        _import(
            conn,
            source_namespace="coop-ch",
            source_observed_at=datetime(2026, 2, 25, 21, 46, tzinfo=UTC),
            content_checksum="coop-2",
            source_path="coop2.csv",
            observations=[
                ProductObservation(
                    identity=identity,
                    name="Bananas Fairtrade",
                    product_url="https://www.coop.ch/p/6495669?x=1",
                    shelf_price=Decimal("3.50"),
                    unified_category="vegetables",
                )
            ],
        )
    with psycopg.connect(app_database_url) as conn:
        rows = conn.execute(
            """
            SELECT name, shelf_price, product_url, id
            FROM catalog_products
            WHERE source_namespace = 'coop-ch' AND source_product_id = '6495669'
            """
        ).fetchall()
        assert len(rows) == 1
        assert rows[0][0] == "Bananas Fairtrade"
        assert Decimal(str(rows[0][1])) == Decimal("3.50")
        assert isinstance(rows[0][3], UUID)


@pytest.mark.integration
def test_deferred_row_leaves_no_product(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Deferred / untrusted identity produces no catalog_products row."""
    with connect_app(app_database_url) as conn:
        _import(
            conn,
            source_namespace="migros-ch",
            source_observed_at=datetime(2025, 12, 30, 15, 22, tzinfo=UTC),
            content_checksum="defer-1",
            source_path="a.csv",
            deferred=[("https://www.migros.ch/de/search", "no id")],
        )
    with psycopg.connect(app_database_url) as conn:
        count = conn.execute(
            """
            SELECT count(*) AS n FROM catalog_products p
            JOIN catalog_snapshots s ON s.id = p.last_snapshot_id
            WHERE s.content_checksum = %s
            """,
            ("defer-1",),
        ).fetchone()
        assert count is not None
        assert count[0] == 0


@pytest.mark.integration
def test_ingest_latest_denner_fixture(
    migrated_database: str,
    app_database_url: str,
    tmp_path: Path,
) -> None:
    """End-to-end ingest of a tiny Denner CSV exercises variant identity + new fields."""
    data_dir = tmp_path / "data"
    retailer_dir = data_dir / "denner-ch-products" / "2025" / "12"
    retailer_dir.mkdir(parents=True)
    csv_path = retailer_dir / "30-14:48.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "name",
                "name_de",
                "url",
                "price",
                "price_text",
                "original_price",
                "original_unit",
                "original_unit_price",
                "unit",
                "unit_price",
                "has_discount",
                "discount_info",
                "image_url",
                "category",
                "unified_category",
                "unified_subcategory",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "name": "Litschis Offenverkauf",
                "name_de": "Litschis",
                "url": (
                    "https://www.denner.ch/de/aktionen-und-sortiment/"
                    "litschis-offenverkauf~p1101270"
                    "?variant=2c8381d3-be7d-41c5-b852-b2a5aff21021"
                ),
                "price": "6.95",
                "price_text": "6.95/kg",
                "original_price": "7.95",
                "original_unit": "kg",
                "original_unit_price": "7.95",
                "unit": "kg",
                "unit_price": "6.95",
                "has_discount": "true",
                "discount_info": "-1",
                "image_url": "https://example/img.jpg",
                "category": "Obst",
                "unified_category": "fruits",
                "unified_subcategory": "misc",
            }
        )
        writer.writerow(
            {
                "name": "Broken",
                "name_de": "",
                "url": "https://www.denner.ch/de/search?q=x",
                "price": "1.00",
                "price_text": "",
                "original_price": "",
                "original_unit": "",
                "original_unit_price": "",
                "unit": "",
                "unit_price": "",
                "has_discount": "",
                "discount_info": "",
                "image_url": "",
                "category": "",
                "unified_category": "",
                "unified_subcategory": "",
            }
        )

    summary = run_ingest(
        data_dir=data_dir,
        database_url=app_database_url,
        retailers=("denner",),
    )
    assert summary.snapshot_count == 1
    assert summary.upserted_count == 1
    assert summary.deferred_count == 1

    with psycopg.connect(app_database_url) as conn:
        product = conn.execute(
            """
            SELECT source_product_id, source_variant_id, name_de,
                   unified_category, original_price, shelf_price,
                   identity_policy_version
            FROM catalog_products
            WHERE source_namespace = 'denner-ch'
              AND source_product_id = '1101270'
            """
        ).fetchone()
        assert product is not None
        assert product[0] == "1101270"
        assert product[1] == "2c8381d3-be7d-41c5-b852-b2a5aff21021"
        assert product[2] == "Litschis"
        assert product[3] == "fruits"
        assert Decimal(str(product[4])) == Decimal("7.95")
        assert Decimal(str(product[5])) == Decimal("6.95")
        assert product[6] == IDENTITY_POLICY_VERSION


@pytest.mark.integration
def test_find_latest_csv_prefers_newest(tmp_path: Path) -> None:
    """Latest-file selection picks the newest timestamped CSV only."""
    root = tmp_path / "migros-ch-products"
    older = root / "2025" / "11"
    newer = root / "2025" / "12"
    older.mkdir(parents=True)
    newer.mkdir(parents=True)
    (older / "01-10:00.csv").write_text("name,url,price\n", encoding="utf-8")
    newest = newer / "30-15:22.csv"
    newest.write_text("name,url,price\n", encoding="utf-8")
    found = find_latest_csv(root)
    assert found == newest
    assert parse_snapshot_timestamp("2025/12/30-15:22.csv") == datetime(
        2025, 12, 30, 15, 22, tzinfo=UTC
    )


@pytest.mark.integration
def test_parse_real_lidl_header_sample() -> None:
    """Latest Lidl dump in data/ parses and yields source identities."""
    data_dir = REPO_ROOT / "data"
    retailer_dir = data_dir / "lidl-ch-products"
    if not retailer_dir.is_dir():
        pytest.skip("data/lidl-ch-products not present")
    latest = find_latest_csv(retailer_dir)
    assert latest is not None
    parsed = parse_csv_snapshot(
        retailer="lidl",
        path=latest,
        data_dir=data_dir,
        retailer_dir=retailer_dir,
    )
    assert parsed.source_namespace == "lidl-ch"
    assert len(parsed.observations) > 100
    sample = parsed.observations[0]
    assert sample.identity.source_product_id.isdigit()
    assert sample.unified_category is not None or sample.source_category is not None
