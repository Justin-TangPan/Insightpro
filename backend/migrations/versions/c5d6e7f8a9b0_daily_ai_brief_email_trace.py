"""Track email delivery against the exact daily AI brief version."""
from alembic import op

revision = "c5d6e7f8a9b0"
down_revision = "b4c5d6e7f8a0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE daily_ai_brief_versions ADD COLUMN email_sent_at TIMESTAMPTZ")
    op.execute("ALTER TABLE daily_ai_brief_versions ADD COLUMN email_recipient_count INT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE daily_ai_brief_versions ADD COLUMN email_failed_count INT NOT NULL DEFAULT 0")
    op.execute("ALTER TABLE daily_ai_brief_versions ADD COLUMN email_template_version TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE daily_ai_brief_versions DROP COLUMN email_template_version")
    op.execute("ALTER TABLE daily_ai_brief_versions DROP COLUMN email_failed_count")
    op.execute("ALTER TABLE daily_ai_brief_versions DROP COLUMN email_recipient_count")
    op.execute("ALTER TABLE daily_ai_brief_versions DROP COLUMN email_sent_at")
