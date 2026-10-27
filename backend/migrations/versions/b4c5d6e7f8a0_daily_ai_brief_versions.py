"""Store versioned daily AI brief snapshots with email sync status."""
from alembic import op

revision = "b4c5d6e7f8a0"
down_revision = "a0b1c2d3e4f5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS daily_ai_brief_versions (
        id BIGSERIAL PRIMARY KEY,
        brief_date TEXT NOT NULL,
        version INT NOT NULL,
        payload JSONB NOT NULL,
        status TEXT NOT NULL,
        candidate_count INT NOT NULL DEFAULT 0,
        selected_count INT NOT NULL DEFAULT 0,
        generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        task_run_id INT,
        email_status TEXT NOT NULL DEFAULT '未触发',
        email_error TEXT,
        UNIQUE (brief_date, version)
    )""")
    op.execute("CREATE INDEX IF NOT EXISTS idx_daily_ai_brief_versions_date ON daily_ai_brief_versions (brief_date, version DESC)")


def downgrade() -> None:
    op.drop_table("daily_ai_brief_versions")