"""Store source-backed daily analyses for each business board."""
from alembic import op

revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE IF NOT EXISTS board_daily_insights (
        board TEXT NOT NULL, insight_date TEXT NOT NULL, fingerprint TEXT NOT NULL,
        analysis TEXT NOT NULL, generated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        PRIMARY KEY (board, insight_date)
    )""")


def downgrade() -> None:
    op.drop_table("board_daily_insights")
