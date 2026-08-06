"""Integration tests for PsycopgRunProductRepository (pipeline product selection).

The shared test database is not wiped between test functions (other suites
leave real rows behind — e.g. `test_catalog_ingest.py` inserts a product
literally named "Vollmilch" with `source_category="Milchprodukte, Eier"`), so
every fixture row here embeds a per-test random tag in every filterable
field (name, name_de, source_category, unified_category). That keeps this
suite's SQL-vs-in-memory comparisons exact without touching shared tables.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

import psycopg
import pytest

from agentic_cataloger.catalog.commands import ImportSnapshotRequest, import_snapshot
from agentic_cataloger.catalog.identity import SourceIdentity
from agentic_cataloger.catalog.ingest_filter import IngestFilter
from agentic_cataloger.catalog.models import ProductObservation
from agentic_cataloger.platform.persistence.catalog_repo import (
    PsycopgProductRepository,
    PsycopgSnapshotRepository,
    PsycopgUnitOfWork,
    connect_app,
)
from agentic_cataloger.platform.persistence.pipeline_repo import (
    PsycopgRunProductRepository,
)
from agentic_cataloger.platform.persistence.taxonomy_repo import (
    PsycopgCategoryRepository,
    PsycopgMembershipRepository,
)
from agentic_cataloger.taxonomy.commands import (
    AssignProductRequest,
    CreateCategoryRequest,
    assign_product_to_leaf,
    create_category,
)


def _clear_taxonomy(conn: psycopg.Connection[Any]) -> None:
    """Wipe taxonomy tables so this test owns a clean one-root tree.

    Established pattern in ``test_taxonomy_persist.py`` — every test there
    clears these two tables first rather than adapting to whatever an
    earlier test left behind.
    """
    conn.execute("DELETE FROM taxonomy_memberships")
    conn.execute("DELETE FROM taxonomy_categories")
    conn.commit()


@dataclass(frozen=True)
class _SeedRow:
    """One fixture product row, source-identified by ``product_id_str``."""

    product_id_str: str
    name: str
    name_de: str | None
    source_category: str | None
    unified_category: str | None


def _rows_for_tag(tag: str) -> list[_SeedRow]:
    """Build fixture rows scoped to ``tag`` so cross-test rows can't collide.

    Row 1/2 match a ``source_category`` substring filter on ``"{tag}
    Milchprodukte"``; row 4 matches only via the exact ``unified_category``
    path; row 3/5 match neither.
    """
    return [
        _SeedRow(
            f"{tag}-1",
            f"{tag} Vollmilch",
            f"{tag} Milch",
            f"{tag} Milchprodukte, Eier",
            f"{tag}-dairy",
        ),
        _SeedRow(
            f"{tag}-2",
            f"{tag} Halbrahm",
            None,
            f"{tag} Milchprodukte, Eier & frische Fertiggerichte",
            f"{tag}-dairy",
        ),
        _SeedRow(
            f"{tag}-3",
            f"{tag} Baguette",
            f"{tag} Brot",
            f"{tag} Backwaren",
            f"{tag}-bakery",
        ),
        _SeedRow(
            f"{tag}-4",
            f"{tag} Griechischer Joghurt",
            f"{tag} Joghurt",
            f"{tag} Kuehlregal",
            f"{tag} Milchprodukte",
        ),
        _SeedRow(
            f"{tag}-5",
            f"{tag} Apfelsaft",
            None,
            f"{tag} Getraenke",
            f"{tag}-beverages",
        ),
    ]


def _seed_products(
    conn: psycopg.Connection[Any], rows: list[_SeedRow]
) -> dict[str, UUID]:
    """Insert fixture products via import_snapshot; return name -> product_id."""
    observations = [
        ProductObservation(
            identity=SourceIdentity("migros-ch", row.product_id_str),
            name=row.name,
            product_url=f"https://www.migros.ch/de/product/{row.product_id_str}",
            shelf_price=Decimal("1.50"),
            name_de=row.name_de,
            source_category=row.source_category,
            unified_category=row.unified_category,
        )
        for row in rows
    ]
    import_snapshot(
        ImportSnapshotRequest(
            source_namespace="migros-ch",
            source_observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            content_checksum=f"pipeline-select-{uuid4()}",
            source_path="test.csv",
            observations=observations,
            deferred=[],
        ),
        snapshots=PsycopgSnapshotRepository(conn),
        products=PsycopgProductRepository(conn),
        uow=PsycopgUnitOfWork(conn),
    )
    products = PsycopgProductRepository(conn)
    ids: dict[str, UUID] = {}
    for row in rows:
        product = products.get_by_source_identity(
            SourceIdentity("migros-ch", row.product_id_str)
        )
        assert product is not None
        ids[row.name] = product.id
    return ids


@pytest.mark.integration
def test_run_product_selection_matches_ingest_filter_in_memory(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """SQL selection returns the same id set as IngestFilter.matches in memory.

    Drift between the two is the only real risk of this SQL read path, so
    this test runs the same criteria object through both and asserts on the
    resulting id sets, not just row counts.
    """
    tag = uuid4().hex[:8]
    rows = _rows_for_tag(tag)
    with connect_app(app_database_url) as conn:
        ids = _seed_products(conn, rows)

        ingest_filter = IngestFilter(source_category=f"{tag} Milchprodukte")
        expected = {
            ids[row.name]
            for row in rows
            if ingest_filter.matches(
                name=row.name,
                name_de=row.name_de,
                source_category=row.source_category,
                unified_category=row.unified_category,
            )
        }
        # Sanity: the fixture actually exercises both match paths.
        assert expected == {
            ids[f"{tag} Vollmilch"],
            ids[f"{tag} Halbrahm"],
            ids[f"{tag} Griechischer Joghurt"],
        }

        selected = PsycopgRunProductRepository(conn).list_for_run(
            ingest_filter=ingest_filter,
            unassigned_only=False,
            limit=None,
        )
        assert {ref.product_id for ref in selected} == expected


@pytest.mark.integration
def test_keyword_filter_matches_ingest_filter_in_memory(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Keyword (name/name_de) matching agrees between SQL and IngestFilter.

    Every fixture row's ``name`` carries the tag, so filtering on the tag
    alone is both a real keyword-substring match and — critically — isolated
    from whatever other tests left in the shared ``catalog_products`` table.
    """
    tag = uuid4().hex[:8]
    rows = _rows_for_tag(tag)
    with connect_app(app_database_url) as conn:
        ids = _seed_products(conn, rows)

        ingest_filter = IngestFilter(keyword=tag)
        expected = {
            ids[row.name]
            for row in rows
            if ingest_filter.matches(
                name=row.name,
                name_de=row.name_de,
                source_category=row.source_category,
                unified_category=row.unified_category,
            )
        }
        assert expected == set(ids.values())

        selected = PsycopgRunProductRepository(conn).list_for_run(
            ingest_filter=ingest_filter,
            unassigned_only=False,
            limit=None,
        )
        assert {ref.product_id for ref in selected} == expected


@pytest.mark.integration
def test_unassigned_only_excludes_membered_products(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """unassigned_only=True hides membered products; False (--reassign) includes them."""
    tag = uuid4().hex[:8]
    rows = _rows_for_tag(tag)
    with connect_app(app_database_url) as conn:
        _clear_taxonomy(conn)
        ids = _seed_products(conn, rows)

        categories = PsycopgCategoryRepository(conn)
        memberships = PsycopgMembershipRepository(conn)
        uow = PsycopgUnitOfWork(conn)
        root = create_category(
            CreateCategoryRequest(name=f"pipeline-persist-root-{tag}"),
            categories=categories,
            memberships=memberships,
            uow=uow,
        ).category
        leaf = create_category(
            CreateCategoryRequest(
                name=f"pipeline-persist-leaf-{tag}", parent_id=root.id
            ),
            categories=categories,
            memberships=memberships,
            uow=uow,
        ).category
        assign_product_to_leaf(
            AssignProductRequest(product_id=ids[f"{tag} Vollmilch"], leaf_id=leaf.id),
            categories=categories,
            memberships=memberships,
            products=PsycopgProductRepository(conn),
            uow=uow,
        )

        ingest_filter = IngestFilter(source_category=f"{tag} Milchprodukte")

        unassigned_only = PsycopgRunProductRepository(conn).list_for_run(
            ingest_filter=ingest_filter,
            unassigned_only=True,
            limit=None,
        )
        selected_ids = {ref.product_id for ref in unassigned_only}
        assert ids[f"{tag} Vollmilch"] not in selected_ids
        assert ids[f"{tag} Halbrahm"] in selected_ids

        reassign = PsycopgRunProductRepository(conn).list_for_run(
            ingest_filter=ingest_filter,
            unassigned_only=False,
            limit=None,
        )
        assert ids[f"{tag} Vollmilch"] in {ref.product_id for ref in reassign}
