"""Keep merged event IDs resolvable to their canonical event."""
from alembic import op
import sqlalchemy as sa

revision = "c8d9e0f1a2b3"
down_revision = "b7c8d9e0f1a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("intelligence_events", sa.Column("merged_into_id", sa.BigInteger(), sa.ForeignKey("intelligence_events.id")))


def downgrade() -> None:
    op.drop_column("intelligence_events", "merged_into_id")
