"""Add candidate discovery and versioned prompt registry."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "d9e0f1a2b3c4"
down_revision = "c8d9e0f1a2b3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intelligence_candidates",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("candidate_key", sa.Text(), nullable=False, unique=True),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("entity_type", sa.Text(), nullable=False, server_default="product_or_topic"),
        sa.Column("business_scopes", postgresql.ARRAY(sa.Text()), nullable=False, server_default=sa.text("ARRAY['community_insights']::text[]")),
        sa.Column("mention_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("discovery_score", sa.Numeric(), nullable=False, server_default="0"),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("resolution_event_id", sa.BigInteger(), sa.ForeignKey("intelligence_events.id")),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("status IN ('pending','approved','ignored')", name="ck_intelligence_candidates_status"),
    )
    op.create_index("idx_intelligence_candidates_status_score", "intelligence_candidates", ["status", "discovery_score"])
    op.create_table(
        "intelligence_candidate_evidence",
        sa.Column("candidate_id", sa.BigInteger(), sa.ForeignKey("intelligence_candidates.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("raw_item_id", sa.BigInteger(), sa.ForeignKey("intelligence_raw_items.id", ondelete="CASCADE"), primary_key=True),
    )
    op.create_table(
        "intelligence_prompts",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("prompt_name", sa.Text(), nullable=False),
        sa.Column("scenario", sa.Text(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="draft"),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("user_prompt_template", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("prompt_name", "version", name="uq_intelligence_prompt_version"),
        sa.CheckConstraint("status IN ('draft','published','archived')", name="ck_intelligence_prompts_status"),
    )
    op.create_index("idx_intelligence_prompts_scenario_status", "intelligence_prompts", ["scenario", "status"])
    op.create_index("uq_intelligence_prompts_published", "intelligence_prompts", ["prompt_name"], unique=True,
                    postgresql_where=sa.text("status='published'"))
    op.add_column("intelligence_analysis", sa.Column("prompt_name", sa.Text()))
    op.add_column("intelligence_analysis", sa.Column("prompt_version", sa.Integer()))
    op.add_column("board_daily_insights", sa.Column("prompt_name", sa.Text()))
    op.add_column("board_daily_insights", sa.Column("prompt_version", sa.Integer()))


def downgrade() -> None:
    op.drop_column("board_daily_insights", "prompt_version")
    op.drop_column("board_daily_insights", "prompt_name")
    op.drop_column("intelligence_analysis", "prompt_version")
    op.drop_column("intelligence_analysis", "prompt_name")
    op.drop_index("uq_intelligence_prompts_published", table_name="intelligence_prompts")
    op.drop_index("idx_intelligence_prompts_scenario_status", table_name="intelligence_prompts")
    op.drop_table("intelligence_prompts")
    op.drop_table("intelligence_candidate_evidence")
    op.drop_index("idx_intelligence_candidates_status_score", table_name="intelligence_candidates")
    op.drop_table("intelligence_candidates")
