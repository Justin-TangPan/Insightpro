"""Persist source-to-delivery inspection results for audit and export."""
from alembic import op
import sqlalchemy as sa

revision = "a5c6e7f8b9d0"
down_revision = "a4c5e6f7b8d9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("intelligence_inspection_results",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_key", sa.Text(), sa.ForeignKey("intelligence_sources.source_key"), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("stages", sa.JSON(), nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('HEALTHY','DEGRADED','FAILED','UNKNOWN','DISABLED')", name="ck_inspection_status"))
    op.create_index("idx_inspection_source_checked", "intelligence_inspection_results",
                    ["source_key", sa.text("checked_at DESC")])


def downgrade() -> None:
    op.drop_index("idx_inspection_source_checked", table_name="intelligence_inspection_results")
    op.drop_table("intelligence_inspection_results")
