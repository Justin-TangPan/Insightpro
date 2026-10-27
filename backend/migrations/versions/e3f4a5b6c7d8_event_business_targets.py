"""Expose the primary and secondary publication targets of one event."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e3f4a5b6c7d8"
down_revision = "d2e3f4a5b6c7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("intelligence_events", sa.Column("primary_business", sa.Text(),
        sa.Computed("business_scopes[1]", persisted=True)))
    op.add_column("intelligence_events", sa.Column("secondary_business", postgresql.ARRAY(sa.Text()),
        sa.Computed("COALESCE(business_scopes[2:cardinality(business_scopes)], ARRAY[]::text[])", persisted=True)))


def downgrade() -> None:
    op.drop_column("intelligence_events", "secondary_business")
    op.drop_column("intelligence_events", "primary_business")
