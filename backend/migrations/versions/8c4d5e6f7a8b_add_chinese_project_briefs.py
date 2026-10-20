"""Store Chinese GitHub project briefs."""
from alembic import op
import sqlalchemy as sa

revision = "8c4d5e6f7a8b"
down_revision = "922ac3fa2764"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("trending_business_eval", sa.Column("summary_zh", sa.Text(), nullable=True))


def downgrade():
    op.drop_column("trending_business_eval", "summary_zh")
