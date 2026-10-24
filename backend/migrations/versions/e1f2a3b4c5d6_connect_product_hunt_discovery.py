"""Connect Product Hunt to Discovery Sentinel.

Downgrade restores fields that still match migration values; an admin change back
to the same value cannot be distinguished from an untouched migration value.
"""
from alembic import op

revision = "e1f2a3b4c5d6"
down_revision = "e0f1a2b3c4d5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE insight_migration_e1_source_schedule_backup (
        source_key TEXT PRIMARY KEY, schedule JSONB)""")
    op.execute("""INSERT INTO insight_migration_e1_source_schedule_backup(source_key,schedule)
        SELECT source_key,schedule FROM intelligence_sources
        WHERE source_key='product_hunt' AND schedule->>'task_key' IS NULL""")
    op.execute("""UPDATE intelligence_sources
        SET schedule=jsonb_set(jsonb_set(schedule,'{task_key}','\"discovery_sentinel_daily\"'::jsonb),
                               '{cron}','\"45 9 * * *\"'::jsonb),updated_at=NOW()
        WHERE source_key='product_hunt' AND schedule->>'task_key' IS NULL""")


def downgrade() -> None:
    op.execute("""UPDATE intelligence_sources source SET schedule=
        CASE WHEN source.schedule->>'task_key'='discovery_sentinel_daily' THEN
            CASE WHEN backup.schedule->>'task_key' IS NULL THEN source.schedule-'task_key'
                 ELSE jsonb_set(source.schedule,'{task_key}',backup.schedule->'task_key') END
        ELSE source.schedule END,
        updated_at=NOW()
        FROM insight_migration_e1_source_schedule_backup backup
        WHERE source.source_key=backup.source_key""")
    op.execute("""UPDATE intelligence_sources source SET schedule=
        CASE WHEN source.schedule->>'cron'='45 9 * * *' THEN
            CASE WHEN backup.schedule->>'cron' IS NULL THEN source.schedule-'cron'
                 ELSE jsonb_set(source.schedule,'{cron}',backup.schedule->'cron') END
        ELSE source.schedule END,
        updated_at=NOW()
        FROM insight_migration_e1_source_schedule_backup backup
        WHERE source.source_key=backup.source_key""")
    op.execute("DROP TABLE insight_migration_e1_source_schedule_backup")
