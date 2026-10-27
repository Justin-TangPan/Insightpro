"""Hold newly generated intelligence events for editorial review."""
from alembic import op

revision = "e7f8a9b0c1d2"
down_revision = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("intelligence_events", "status", server_default="pending_review")


def downgrade() -> None:
    op.alter_column("intelligence_events", "status", server_default="active")
