"""Expose bounded pipeline counters on the existing task run table."""
from alembic import op
import sqlalchemy as sa

revision = "a2c3e4f5b6d7"
down_revision = "a1c2e3f4b5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("platform_task_runs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    for name in ("input_count", "new_count", "changed_count", "skipped_count", "failed_count"):
        op.add_column("platform_task_runs", sa.Column(name, sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    for name in ("failed_count", "skipped_count", "changed_count", "new_count", "input_count"):
        op.drop_column("platform_task_runs", name)
    op.drop_column("platform_task_runs", "heartbeat_at")
