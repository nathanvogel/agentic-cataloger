"""``deferred_items`` — human-review rows the agent won't guess."""

from __future__ import annotations

from alembic import op

revision = "005_review_deferred_items"
down_revision = "004_taxonomy_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE deferred_items (
            id UUID PRIMARY KEY,
            product_id UUID NOT NULL REFERENCES catalog_products (id),
            stage TEXT NOT NULL,
            reason_code TEXT NOT NULL,
            attempt_count INTEGER NOT NULL,
            payload_snapshot JSONB NOT NULL,
            evidence_span TEXT,
            trace_id TEXT,
            status TEXT NOT NULL DEFAULT 'open',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT deferred_items_stage_chk
                CHECK (stage IN ('discover_create', 'assign')),
            CONSTRAINT deferred_items_reason_code_chk
                CHECK (reason_code IN ('unknown', 'defer', 'low_confidence')),
            CONSTRAINT deferred_items_status_chk
                CHECK (status IN ('open'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX deferred_items_product_id_idx ON deferred_items (product_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS deferred_items_product_id_idx")
    op.execute("DROP TABLE IF EXISTS deferred_items")
