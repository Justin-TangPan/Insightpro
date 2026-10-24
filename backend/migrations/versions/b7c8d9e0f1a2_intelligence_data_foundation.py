"""Add the additive V2 source and intelligence data foundation."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "b7c8d9e0f1a2"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "intelligence_sources",
        sa.Column("source_key", sa.Text(), primary_key=True),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("adapter", sa.Text(), nullable=False),
        sa.Column("base_url", sa.Text()),
        sa.Column("business_scopes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("authority", sa.Text(), nullable=False, server_default="P1"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("schedule", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("config", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("health_status", sa.Text(), nullable=False, server_default="unknown"),
        sa.Column("last_success_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint("authority IN ('P0','P1','P2')", name="ck_intelligence_sources_authority"),
    )
    op.create_table(
        "intelligence_entities",
        sa.Column("entity_key", sa.Text(), primary_key=True),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("canonical_name", sa.Text(), nullable=False),
        sa.Column("aliases", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "intelligence_raw_items",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_key", sa.Text(), sa.ForeignKey("intelligence_sources.source_key"), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("content_hash", sa.Text()),
        sa.UniqueConstraint("source_key", "external_id", name="uq_intelligence_raw_source_external"),
    )
    op.create_index("idx_intelligence_raw_observed", "intelligence_raw_items", ["observed_at"])
    op.create_table(
        "intelligence_events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_key", sa.Text(), nullable=False, unique=True),
        sa.Column("entity_key", sa.Text(), sa.ForeignKey("intelligence_entities.entity_key")),
        sa.Column("event_type", sa.Text(), nullable=False),
        sa.Column("business_scopes", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("summary", sa.Text()),
        sa.Column("event_at", sa.DateTime(timezone=True)),
        sa.Column("published_at", sa.DateTime(timezone=True)),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("tags", postgresql.JSONB(), nullable=False, server_default="[]"),
        sa.Column("scores", postgresql.JSONB(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_intelligence_events_seen", "intelligence_events", ["last_seen_at"])
    op.create_table(
        "intelligence_event_evidence",
        sa.Column("event_id", sa.BigInteger(), sa.ForeignKey("intelligence_events.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("raw_item_id", sa.BigInteger(), sa.ForeignKey("intelligence_raw_items.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("evidence_role", sa.Text(), nullable=False, server_default="source"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_table(
        "intelligence_metric_snapshots",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("entity_key", sa.Text(), sa.ForeignKey("intelligence_entities.entity_key"), nullable=False),
        sa.Column("source_key", sa.Text(), sa.ForeignKey("intelligence_sources.source_key"), nullable=False),
        sa.Column("raw_item_id", sa.BigInteger(), sa.ForeignKey("intelligence_raw_items.id")),
        sa.Column("metric_key", sa.Text(), nullable=False),
        sa.Column("metric_value", sa.Numeric(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("entity_key", "source_key", "metric_key", "observed_at", name="uq_intelligence_metric_observation"),
    )
    op.create_index("idx_intelligence_metrics_entity_time", "intelligence_metric_snapshots", ["entity_key", "metric_key", "observed_at"])
    op.create_table(
        "intelligence_audit",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("object_type", sa.Text(), nullable=False),
        sa.Column("object_key", sa.Text(), nullable=False),
        sa.Column("before_state", postgresql.JSONB()),
        sa.Column("after_state", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_intelligence_audit_created", "intelligence_audit", ["created_at"])

    op.execute("""
        INSERT INTO intelligence_sources (source_key, name, adapter, base_url, business_scopes, authority, schedule)
        VALUES
          ('github_trending', 'GitHub Trending', 'github_trending', 'https://github.com/trending', ARRAY['technology_ecosystem'], 'P0', jsonb_build_object('cron','30 8 * * *','timezone','Asia/Shanghai','task_key','github_daily')),
          ('product_hunt', 'Product Hunt', 'product_hunt_feed', 'https://www.producthunt.com/feed', ARRAY['ai_applications'], 'P2', jsonb_build_object('cron','30 9 * * *','timezone','Asia/Shanghai')),
          ('community_zhihu', '知乎热榜', 'community_zhihu', 'https://api.zhihu.com/topstory/hot-lists/total', ARRAY['community_insights'], 'P2', jsonb_build_object('interval_minutes',15,'task_key','daily_crawl')),
          ('community_csdn', 'CSDN 热榜', 'community_csdn', 'https://blog.csdn.net/phoenix/web/blog/hotRank', ARRAY['community_insights'], 'P2', jsonb_build_object('interval_minutes',15,'task_key','daily_crawl')),
          ('community_tencent', '腾讯云开发者社区', 'community_tencent', 'https://developer.cloud.tencent.com/', ARRAY['community_insights'], 'P2', jsonb_build_object('interval_minutes',15,'task_key','daily_crawl')),
          ('community_baidu', '百度热搜', 'community_baidu', 'https://top.baidu.com/', ARRAY['community_insights'], 'P2', jsonb_build_object('interval_minutes',15,'task_key','daily_crawl')),
          ('aliyun_solutions', '阿里云解决方案', 'aliyun_solutions', 'https://cn.aliyun.com/solution/tech-solution/', ARRAY['solutions'], 'P0', jsonb_build_object('cron','0 9 * * *','timezone','Asia/Shanghai','task_key','solution_catalogs_daily')),
          ('huawei_solutions', '华为云解决方案', 'huawei_solutions', 'https://www.huaweicloud.com/solution/reference-architecture.html', ARRAY['solutions'], 'P0', jsonb_build_object('cron','0 9 * * *','timezone','Asia/Shanghai','task_key','solution_catalogs_daily')),
          ('ai_app_official', '官方 AI 应用动态', 'ai_applications_official', NULL, ARRAY['ai_applications'], 'P1', jsonb_build_object('cron','30 9 * * *','timezone','Asia/Shanghai','task_key','ai_applications_daily')),
          ('competitor_news', '友商官方动态', 'competitor_news', NULL, ARRAY['competitor_dynamics'], 'P1', jsonb_build_object('cron','2 9 * * *','timezone','Asia/Shanghai','task_key','competitor_daily')),
          ('hacker_news', 'Hacker News', 'hacker_news_api', 'https://hacker-news.firebaseio.com/v0/topstories.json', ARRAY['technology_ecosystem','community_insights'], 'P1', jsonb_build_object('cron','45 9 * * *','timezone','Asia/Shanghai','task_key','discovery_sentinel_daily')),
          ('hugging_face', 'Hugging Face Trending', 'hugging_face_api', 'https://huggingface.co/api/models', ARRAY['technology_ecosystem'], 'P1', jsonb_build_object('cron','45 9 * * *','timezone','Asia/Shanghai','task_key','discovery_sentinel_daily')),
          ('arxiv_ai', 'arXiv AI Research', 'arxiv_api', 'https://export.arxiv.org/api/query', ARRAY['technology_ecosystem'], 'P1', jsonb_build_object('cron','45 9 * * *','timezone','Asia/Shanghai','task_key','discovery_sentinel_daily'))
        ON CONFLICT (source_key) DO NOTHING
    """)


def downgrade() -> None:
    op.drop_index("idx_intelligence_audit_created", table_name="intelligence_audit")
    op.drop_table("intelligence_audit")
    op.drop_table("intelligence_metric_snapshots")
    op.drop_table("intelligence_event_evidence")
    op.drop_index("idx_intelligence_events_seen", table_name="intelligence_events")
    op.drop_table("intelligence_events")
    op.drop_index("idx_intelligence_raw_observed", table_name="intelligence_raw_items")
    op.drop_table("intelligence_raw_items")
    op.drop_table("intelligence_entities")
    op.drop_table("intelligence_sources")
