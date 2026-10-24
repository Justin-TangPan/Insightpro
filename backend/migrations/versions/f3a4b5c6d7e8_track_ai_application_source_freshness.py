"""Track the source snapshot behind each official application analysis."""
from alembic import op

revision = "f3a4b5c6d7e8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE vendor_ai_applications ADD COLUMN IF NOT EXISTS source_updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()")
    op.execute("ALTER TABLE vendor_ai_applications ADD COLUMN IF NOT EXISTS source_fingerprint TEXT")
    op.execute("ALTER TABLE vendor_ai_applications ADD COLUMN IF NOT EXISTS analyzed_source_fingerprint TEXT")


def downgrade() -> None:
    op.execute("ALTER TABLE vendor_ai_applications DROP COLUMN IF EXISTS analyzed_source_fingerprint")
    op.execute("ALTER TABLE vendor_ai_applications DROP COLUMN IF EXISTS source_fingerprint")
    op.execute("ALTER TABLE vendor_ai_applications DROP COLUMN IF EXISTS source_updated_at")
