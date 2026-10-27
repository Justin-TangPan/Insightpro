"""Move registered source collection into the 08:00 hour."""
from alembic import op

revision = "f9a0b1c2d3e4"
down_revision = "f8a9b0c1d2e3"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("""WITH times(task_key, cron) AS (VALUES
        ('github_daily','0 8 * * *'),
        ('solution_catalogs_daily','10 8 * * *'),
        ('competitor_daily','25 8 * * *'),
        ('ai_applications_daily','35 8 * * *'),
        ('discovery_sentinel_daily','45 8 * * *'))
        UPDATE intelligence_sources source SET
          schedule=jsonb_set(jsonb_set(source.schedule,'{previous_cron_rc58}',source.schedule->'cron',TRUE),
                             '{cron}',to_jsonb(times.cron),TRUE),updated_at=NOW()
        FROM times WHERE source.schedule->>'task_key'=times.task_key
          AND source.schedule ? 'cron' AND source.schedule->>'cron'<>times.cron""")
    op.execute("""UPDATE intelligence_sources SET
        schedule=jsonb_build_object('task_key','community_insights_daily','cron','30 8 * * *',
                                    'timezone','Asia/Shanghai','previous_schedule_rc58',schedule),
        updated_at=NOW()
        WHERE adapter IN ('community_zhihu','community_baidu','community_tencent','community_csdn')""")


def downgrade():
    op.execute("""UPDATE intelligence_sources SET
        schedule=schedule->'previous_schedule_rc58',updated_at=NOW()
        WHERE schedule ? 'previous_schedule_rc58'""")
    op.execute("""UPDATE intelligence_sources SET
        schedule=jsonb_set(schedule-'previous_cron_rc58','{cron}',schedule->'previous_cron_rc58',TRUE),updated_at=NOW()
        WHERE schedule ? 'previous_cron_rc58'""")
