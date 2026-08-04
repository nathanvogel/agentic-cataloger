"""Catalog snapshots (immutable) and products under durable source identity."""

from __future__ import annotations

from alembic import op

revision = "002_catalog_ingest"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE catalog_snapshots (
            id UUID PRIMARY KEY,
            source_namespace TEXT NOT NULL,
            source_observed_at TIMESTAMPTZ NOT NULL,
            content_checksum TEXT NOT NULL,
            adapter_version TEXT NOT NULL,
            source_path TEXT NOT NULL,
            registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT catalog_snapshots_checksum_adapter_uq
                UNIQUE (content_checksum, adapter_version)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE catalog_products (
            id UUID PRIMARY KEY,
            source_namespace TEXT NOT NULL,
            source_product_id TEXT NOT NULL,
            source_variant_id TEXT,
            name TEXT NOT NULL,
            name_de TEXT,
            product_url TEXT NOT NULL,
            image_url TEXT,
            shelf_price NUMERIC(24, 12) NOT NULL,
            currency TEXT NOT NULL DEFAULT 'CHF',
            price_text TEXT,
            unit TEXT,
            unit_price NUMERIC(24, 12),
            original_price NUMERIC(24, 12),
            original_unit TEXT,
            original_unit_price NUMERIC(24, 12),
            has_discount BOOLEAN,
            discount_info TEXT,
            source_category TEXT,
            unified_category TEXT,
            unified_subcategory TEXT,
            identity_policy_version TEXT NOT NULL,
            last_snapshot_id UUID NOT NULL
                REFERENCES catalog_snapshots (id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT catalog_products_source_identity_uq
                UNIQUE NULLS NOT DISTINCT (
                    source_namespace,
                    source_product_id,
                    source_variant_id
                )
        )
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION catalog_snapshots_reject_mutation()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                RAISE EXCEPTION
                    'catalog_snapshots rows are immutable (delete rejected)'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            IF NEW.id IS DISTINCT FROM OLD.id
               OR NEW.source_namespace IS DISTINCT FROM OLD.source_namespace
               OR NEW.source_observed_at IS DISTINCT FROM OLD.source_observed_at
               OR NEW.content_checksum IS DISTINCT FROM OLD.content_checksum
               OR NEW.adapter_version IS DISTINCT FROM OLD.adapter_version
               OR NEW.source_path IS DISTINCT FROM OLD.source_path
               OR NEW.registered_at IS DISTINCT FROM OLD.registered_at
            THEN
                RAISE EXCEPTION
                    'catalog_snapshots identifying fields are immutable'
                    USING ERRCODE = 'integrity_constraint_violation';
            END IF;
            RETURN NEW;
        END;
        $$
        """
    )
    op.execute(
        """
        CREATE TRIGGER catalog_snapshots_immutable
        BEFORE UPDATE OR DELETE ON catalog_snapshots
        FOR EACH ROW
        EXECUTE FUNCTION catalog_snapshots_reject_mutation()
        """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS catalog_snapshots_immutable ON catalog_snapshots"
    )
    op.execute("DROP FUNCTION IF EXISTS catalog_snapshots_reject_mutation()")
    op.execute("DROP TABLE IF EXISTS catalog_products")
    op.execute("DROP TABLE IF EXISTS catalog_snapshots")
