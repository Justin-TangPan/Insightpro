"""Track each subscriber brief independently for safe retry."""
from alembic import op
import sqlalchemy as sa

revision = "e0f1a2b3c4d5"
down_revision = "d9e0f1a2b3c4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "email_delivery_attempts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("subscriber_id", sa.Integer(), nullable=False),
        sa.Column("recipient_email", sa.Text(), nullable=False),
        sa.Column("delivery_date", sa.Date(), nullable=False),
        sa.Column("delivery_type", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("last_error", sa.Text()),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("subscriber_id", "delivery_date", "delivery_type", name="uq_email_delivery_subscriber_day_type"),
        sa.CheckConstraint("delivery_type IN ('business','technical')", name="ck_email_delivery_type"),
        sa.CheckConstraint("status IN ('sent','failed')", name="ck_email_delivery_status"),
    )
    op.create_index("idx_email_delivery_date_status", "email_delivery_attempts", ["delivery_date", "status"])


def downgrade() -> None:
    op.drop_index("idx_email_delivery_date_status", table_name="email_delivery_attempts")
    op.drop_table("email_delivery_attempts")
