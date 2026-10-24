"""Add GitHub Search as a scheduled Discovery Sentinel source."""
from alembic import op

revision = "f2a3b4c5d6e7"
down_revision = "e1f2a3b4c5d6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""INSERT INTO intelligence_sources
        (source_key,name,adapter,base_url,business_scopes,authority,priority,schedule,enabled)
        VALUES ('github_search','GitHub AI/Agent Repository Search','github_search_api',
          'https://api.github.com/search/repositories',ARRAY['technology_ecosystem'],'P1',35,
          '{"task_key":"discovery_sentinel_daily","cron":"45 9 * * *","timezone":"Asia/Shanghai"}'::jsonb,TRUE)
        ON CONFLICT (source_key) DO NOTHING""")


def downgrade() -> None:
    op.execute("""UPDATE intelligence_sources SET enabled=FALSE,updated_at=NOW()
        WHERE source_key='github_search' AND adapter='github_search_api'""")
