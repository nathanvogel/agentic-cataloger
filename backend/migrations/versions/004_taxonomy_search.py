"""Enable pg_trgm and add a GIN trigram index for category name search."""

from __future__ import annotations

from alembic import op

revision = "004_taxonomy_search"
down_revision = "003_taxonomy_tree"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE INDEX taxonomy_categories_name_trgm_idx
            ON taxonomy_categories USING GIN (name gin_trgm_ops)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS taxonomy_categories_name_trgm_idx")
    op.execute("DROP EXTENSION IF EXISTS pg_trgm")
