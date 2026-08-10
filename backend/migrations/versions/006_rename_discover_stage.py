"""Rename deferred_items stage value discover_create → discover."""

from __future__ import annotations

from alembic import op

revision = "006_rename_discover_stage"
down_revision = "005_review_deferred_items"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE deferred_items
        SET stage = 'discover'
        WHERE stage = 'discover_create'
        """
    )
    op.execute(
        """
        ALTER TABLE deferred_items
        DROP CONSTRAINT deferred_items_stage_chk
        """
    )
    op.execute(
        """
        ALTER TABLE deferred_items
        ADD CONSTRAINT deferred_items_stage_chk
            CHECK (stage IN ('discover', 'assign'))
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE deferred_items
        SET stage = 'discover_create'
        WHERE stage = 'discover'
        """
    )
    op.execute(
        """
        ALTER TABLE deferred_items
        DROP CONSTRAINT deferred_items_stage_chk
        """
    )
    op.execute(
        """
        ALTER TABLE deferred_items
        ADD CONSTRAINT deferred_items_stage_chk
            CHECK (stage IN ('discover_create', 'assign'))
        """
    )
