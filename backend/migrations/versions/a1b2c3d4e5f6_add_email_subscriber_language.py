"""store each subscriber's daily digest language"""
from alembic import op
import sqlalchemy as sa

revision = "a1b2c3d4e5f6"
down_revision = "9d5e6f7a8b9c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("email_subscribers", sa.Column("language", sa.Text(), nullable=False, server_default="zh"))


def downgrade():
    op.drop_column("email_subscribers", "language")
