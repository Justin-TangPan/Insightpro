"""Track backend AI calls and whether provider token usage was supplied."""
from alembic import op
import sqlalchemy as sa

revision = "9d5e6f7a8b9c"
down_revision = "8c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade():
    op.alter_column("ai_usage_records", "user_id", existing_type=sa.UUID(), nullable=True)
    op.add_column("ai_usage_records", sa.Column("usage_reported", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE ai_usage_records SET usage_reported = TRUE WHERE input_tokens > 0 OR output_tokens > 0")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT EXISTS (SELECT 1 FROM ai_usage_records WHERE user_id IS NULL)")).scalar():
        raise RuntimeError("Backend usage records have no user; restore them before downgrading")
    op.drop_column("ai_usage_records", "usage_reported")
    op.alter_column("ai_usage_records", "user_id", existing_type=sa.UUID(), nullable=False)
