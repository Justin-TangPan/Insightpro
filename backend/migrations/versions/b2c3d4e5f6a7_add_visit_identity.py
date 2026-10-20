"""Add verified user identity to page visits."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("page_visits", sa.Column("user_id", postgresql.UUID(as_uuid=False), nullable=True))
    op.add_column("page_visits", sa.Column("user_email", sa.Text(), nullable=True))
    op.add_column("page_visits", sa.Column("display_name", sa.Text(), nullable=True))
    op.create_index("idx_page_visits_user", "page_visits", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("idx_page_visits_user", table_name="page_visits")
    op.drop_column("page_visits", "display_name")
    op.drop_column("page_visits", "user_email")
    op.drop_column("page_visits", "user_id")
