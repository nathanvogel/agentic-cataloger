"""Integration tests for taxonomy tree + leaf membership."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, final
from uuid import UUID, uuid4

import psycopg
import pytest

from pricecomp.catalog.commands import ImportSnapshotRequest, import_snapshot
from pricecomp.catalog.identity import SourceIdentity
from pricecomp.catalog.models import ProductObservation
from pricecomp.platform.persistence.catalog_repo import (
    PsycopgProductRepository,
    PsycopgSnapshotRepository,
    PsycopgUnitOfWork,
    connect_app,
)
from pricecomp.platform.persistence.taxonomy_repo import (
    PsycopgCategoryRepository,
    PsycopgMembershipRepository,
    PsycopgProductExistence,
)
from pricecomp.platform.taxonomy.runner import (
    ProductRef,
    format_taxonomy_tree,
    run_assign_product,
    run_create_category,
    run_reparent_category,
    run_show_taxonomy,
)
from pricecomp.taxonomy.commands import (
    AssignProductRequest,
    CreateCategoryRequest,
    assign_product_to_leaf,
    create_category,
)
from pricecomp.taxonomy.errors import CycleError, NotLeafError
from pricecomp.taxonomy.ports import ProductExistence


def _clear_taxonomy(conn: psycopg.Connection[Any]) -> None:
    """Wipe taxonomy tables so each test owns a clean one-root tree."""
    conn.execute("DELETE FROM taxonomy_memberships")
    conn.execute("DELETE FROM taxonomy_categories")
    conn.commit()


def _seed_product(conn: psycopg.Connection[Any], *, product_id: str = "100") -> UUID:
    """Insert one catalog product via import_snapshot; return its app id."""
    result = import_snapshot(
        ImportSnapshotRequest(
            source_namespace="migros-ch",
            source_observed_at=datetime(2026, 1, 1, tzinfo=UTC),
            content_checksum=f"tax-{product_id}-{uuid4()}",
            source_path="test.csv",
            observations=[
                ProductObservation(
                    identity=SourceIdentity("migros-ch", product_id),
                    name="Test milk",
                    product_url=f"https://www.migros.ch/de/product/{product_id}",
                    shelf_price=Decimal("1.50"),
                )
            ],
            deferred=[],
        ),
        snapshots=PsycopgSnapshotRepository(conn),
        products=PsycopgProductRepository(conn),
        uow=PsycopgUnitOfWork(conn),
    )
    product = PsycopgProductRepository(conn).get_by_source_identity(
        SourceIdentity("migros-ch", product_id)
    )
    assert product is not None
    assert result.upserted_count == 1
    return product.id


@final
@dataclass
class _FixedProductExistence(ProductExistence):
    product_id: UUID

    def exists(self, product_id: UUID) -> bool:
        return product_id == self.product_id


@pytest.mark.integration
def test_create_show_assign_move(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Create root+children, show tree, assign, then move on re-assign."""
    with connect_app(app_database_url) as conn:
        _clear_taxonomy(conn)
        product_uuid = _seed_product(conn)

    root = run_create_category(
        name="Dairy",
        preferred_comparable_unit="L",
        database_url=app_database_url,
    ).category
    leaf_a = run_create_category(
        name="Cow milk",
        parent_id=root.id,
        database_url=app_database_url,
    ).category
    leaf_b = run_create_category(
        name="Goat milk",
        parent_id=root.id,
        database_url=app_database_url,
    ).category

    tree_text = format_taxonomy_tree(run_show_taxonomy(database_url=app_database_url))
    assert str(root.id) in tree_text
    assert "Cow milk" in tree_text
    assert "unit=L" in tree_text

    first = run_assign_product(
        product=ProductRef(product_id=product_uuid),
        leaf_id=leaf_a.id,
        database_url=app_database_url,
    )
    assert first.moved is False
    assert first.membership.category_id == leaf_a.id

    second = run_assign_product(
        product=ProductRef(product_id=product_uuid),
        leaf_id=leaf_b.id,
        database_url=app_database_url,
    )
    assert second.moved is True
    assert second.membership.category_id == leaf_b.id

    with connect_app(app_database_url) as conn:
        rows = conn.execute(
            "SELECT product_id, category_id FROM taxonomy_memberships"
        ).fetchall()
        assert len(rows) == 1
        assert rows[0]["category_id"] == leaf_b.id


@pytest.mark.integration
def test_assign_non_leaf_and_cycle_rejected(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Assign to non-leaf and cyclic reparent fail with domain errors."""
    with connect_app(app_database_url) as conn:
        _clear_taxonomy(conn)
        product_uuid = _seed_product(conn, product_id="200")
        categories = PsycopgCategoryRepository(conn)
        memberships = PsycopgMembershipRepository(conn)
        uow = PsycopgUnitOfWork(conn)

        root = create_category(
            CreateCategoryRequest(name="Root"),
            categories=categories,
            memberships=memberships,
            uow=uow,
        ).category
        child = create_category(
            CreateCategoryRequest(name="Child", parent_id=root.id),
            categories=categories,
            memberships=memberships,
            uow=uow,
        ).category
        grandchild = create_category(
            CreateCategoryRequest(name="Grand", parent_id=child.id),
            categories=categories,
            memberships=memberships,
            uow=uow,
        ).category

        with pytest.raises(NotLeafError):
            assign_product_to_leaf(
                AssignProductRequest(product_id=product_uuid, leaf_id=root.id),
                categories=categories,
                memberships=memberships,
                products=_FixedProductExistence(product_uuid),
                uow=uow,
            )

    with pytest.raises(CycleError):
        run_reparent_category(
            category_id=child.id,
            new_parent_id=grandchild.id,
            database_url=app_database_url,
        )


@pytest.mark.integration
def test_unique_product_membership_at_db(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Raw second INSERT for the same product_id is rejected by UNIQUE."""
    with connect_app(app_database_url) as conn:
        _clear_taxonomy(conn)
        product_uuid = _seed_product(conn, product_id="300")

    root = run_create_category(name="Root", database_url=app_database_url).category
    leaf = run_create_category(
        name="Leaf",
        parent_id=root.id,
        database_url=app_database_url,
    ).category
    run_assign_product(
        product=ProductRef(product_id=product_uuid),
        leaf_id=leaf.id,
        database_url=app_database_url,
    )

    with connect_app(app_database_url) as conn:
        sibling_id = uuid4()
        conn.execute(
            """
            INSERT INTO taxonomy_categories (id, name, parent_id)
            VALUES (%s, %s, %s)
            """,
            (sibling_id, "Sibling", root.id),
        )
        conn.commit()
        with pytest.raises(psycopg.Error):
            conn.execute(
                """
                INSERT INTO taxonomy_memberships (product_id, category_id)
                VALUES (%s, %s)
                """,
                (product_uuid, sibling_id),
            )
            conn.commit()


@pytest.mark.integration
def test_ingest_does_not_wipe_membership(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """Re-importing a product does not delete taxonomy_memberships rows."""
    with connect_app(app_database_url) as conn:
        _clear_taxonomy(conn)
        product_uuid = _seed_product(conn, product_id="400")

    root = run_create_category(name="Root", database_url=app_database_url).category
    run_assign_product(
        product=ProductRef(product_id=product_uuid),
        leaf_id=root.id,
        database_url=app_database_url,
    )

    with connect_app(app_database_url) as conn:
        # Same source identity, new checksum → upsert observations only.
        import_snapshot(
            ImportSnapshotRequest(
                source_namespace="migros-ch",
                source_observed_at=datetime(2026, 1, 2, tzinfo=UTC),
                content_checksum=f"tax-reimport-{uuid4()}",
                source_path="test2.csv",
                observations=[
                    ProductObservation(
                        identity=SourceIdentity("migros-ch", "400"),
                        name="Test milk v2",
                        product_url="https://www.migros.ch/de/product/400",
                        shelf_price=Decimal("1.60"),
                    )
                ],
                deferred=[],
            ),
            snapshots=PsycopgSnapshotRepository(conn),
            products=PsycopgProductRepository(conn),
            uow=PsycopgUnitOfWork(conn),
        )
        row = conn.execute(
            """
            SELECT category_id FROM taxonomy_memberships WHERE product_id = %s
            """,
            (product_uuid,),
        ).fetchone()
        assert row is not None
        assert row["category_id"] == root.id
        product = PsycopgProductRepository(conn).get_by_source_identity(
            SourceIdentity("migros-ch", "400")
        )
        assert product is not None
        assert product.name == "Test milk v2"
        assert product.id == product_uuid


@pytest.mark.integration
def test_product_existence_adapter(
    migrated_database: str,
    app_database_url: str,
) -> None:
    """PsycopgProductExistence mirrors catalog_products rows."""
    with connect_app(app_database_url) as conn:
        product_uuid = _seed_product(conn, product_id="500")
        lookup = PsycopgProductExistence(conn)
        assert lookup.exists(product_uuid) is True
        assert lookup.exists(uuid4()) is False
