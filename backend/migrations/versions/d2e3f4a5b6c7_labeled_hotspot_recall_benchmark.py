"""Store independently sourced and reviewed hotspot benchmark references."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d2e3f4a5b6c7"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intelligence_recall_benchmark",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text(), nullable=False),
        sa.Column("reference_source", sa.Text(), nullable=False),
        sa.Column("reference_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("is_relevant", sa.Boolean(), nullable=False),
        sa.Column("label_reason", sa.Text(), nullable=False),
        sa.Column("labeled_by", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("canonical_url", "reference_at", name="uq_intelligence_recall_reference"),
    )
    op.create_index("idx_intelligence_recall_reference_at", "intelligence_recall_benchmark", ["reference_at"])


def downgrade() -> None:
    op.drop_index("idx_intelligence_recall_reference_at", table_name="intelligence_recall_benchmark")
    op.drop_table("intelligence_recall_benchmark")
