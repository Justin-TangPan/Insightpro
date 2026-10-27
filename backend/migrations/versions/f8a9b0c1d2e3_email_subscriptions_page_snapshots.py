"""Independent brief schedules and immutable published page content."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB

revision = "f8a9b0c1d2e3"
down_revision = "e7f8a9b0c1d2"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table("email_subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("recipient_id", sa.Integer(), sa.ForeignKey("email_subscribers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("email_type", sa.Text(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("weekdays", ARRAY(sa.Integer()), nullable=False),
        sa.Column("send_time", sa.Text(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="Asia/Shanghai"),
        sa.UniqueConstraint("recipient_id", "email_type"),
        sa.CheckConstraint("email_type IN ('business','technical')"),
    )
    op.execute("""INSERT INTO email_subscriptions (recipient_id,email_type,weekdays,send_time)
        SELECT id,kind,weekdays,send_time FROM email_subscribers
        CROSS JOIN (VALUES ('business'),('technical')) AS types(kind)""")
    op.add_column("email_content_snapshots", sa.Column("email_type", sa.Text(), nullable=False, server_default="business"))
    op.add_column("email_content_snapshots", sa.Column("source_snapshot", JSONB()))
    op.add_column("email_content_snapshots", sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("email_delivery_attempts", sa.Column("subscription_id", sa.Integer(), sa.ForeignKey("email_subscriptions.id")))
    op.execute("""UPDATE email_delivery_attempts d SET subscription_id=s.id
        FROM email_subscriptions s WHERE s.recipient_id=d.subscriber_id AND s.email_type=d.delivery_type""")
    op.create_table("page_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("snapshot_date", sa.Date(), nullable=False),
        sa.Column("page", sa.Text(), nullable=False),
        sa.Column("content", JSONB(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.UniqueConstraint("snapshot_date", "page"))


def downgrade():
    op.drop_table("page_snapshots")
    op.drop_column("email_delivery_attempts", "subscription_id")
    op.drop_column("email_content_snapshots", "version")
    op.drop_column("email_content_snapshots", "source_snapshot")
    op.drop_column("email_content_snapshots", "email_type")
    op.drop_table("email_subscriptions")
