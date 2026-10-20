"""Store one AI homepage recommendation per day."""
from alembic import op
import sqlalchemy as sa

revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "homepage_daily_recommendations",
        sa.Column("insight_date", sa.Text(), primary_key=True),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
    )


def downgrade() -> None:
    op.drop_table("homepage_daily_recommendations")
