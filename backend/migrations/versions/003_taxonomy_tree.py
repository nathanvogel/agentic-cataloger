"""Taxonomy categories (rooted tree) and product↔leaf membership."""

from __future__ import annotations

from alembic import op

revision = "003_taxonomy_tree"
down_revision = "002_catalog_ingest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE taxonomy_categories (
            id UUID PRIMARY KEY,
            name TEXT NOT NULL,
            parent_id UUID REFERENCES taxonomy_categories (id),
            preferred_comparable_unit TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT taxonomy_categories_no_self_parent_chk
                CHECK (parent_id IS DISTINCT FROM id)
        )
        """
    )
    op.execute(
        """
        CREATE UNIQUE INDEX taxonomy_categories_one_root_uq
            ON taxonomy_categories ((1))
            WHERE parent_id IS NULL
        """
    )
    op.execute(
        """
        CREATE TABLE taxonomy_memberships (
            product_id UUID PRIMARY KEY
                REFERENCES catalog_products (id),
            category_id UUID NOT NULL
                REFERENCES taxonomy_categories (id),
            assigned_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS taxonomy_memberships")
    op.execute("DROP INDEX IF EXISTS taxonomy_categories_one_root_uq")
    op.execute("DROP TABLE IF EXISTS taxonomy_categories")
