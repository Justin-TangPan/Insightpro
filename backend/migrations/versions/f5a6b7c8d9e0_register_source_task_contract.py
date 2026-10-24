"""Register existing collectors against their source rows.

Downgrade restores fields that still match migration values; an admin change back
to the same value cannot be distinguished from an untouched migration value.
"""
from alembic import op

revision = "f5a6b7c8d9e0"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE insight_migration_f5_source_schedule_backup (
        source_key TEXT PRIMARY KEY, schedule JSONB)""")
    op.execute("""INSERT INTO insight_migration_f5_source_schedule_backup(source_key,schedule)
        SELECT source_key,schedule FROM intelligence_sources
        WHERE source_key IN ('github_trending','aliyun_solutions','huawei_solutions','ai_app_official')
          AND schedule->>'task_key' IS NULL""")
    op.execute("""UPDATE intelligence_sources
        SET schedule=COALESCE(schedule,'{}'::jsonb) || jsonb_build_object(
            'task_key', CASE source_key
                WHEN 'github_trending' THEN 'github_daily'
                WHEN 'aliyun_solutions' THEN 'solution_catalogs_daily'
                WHEN 'huawei_solutions' THEN 'solution_catalogs_daily'
                WHEN 'ai_app_official' THEN 'ai_applications_daily'
            END,
            'timezone', COALESCE(schedule->>'timezone','Asia/Shanghai')),
            updated_at=NOW()
        WHERE source_key IN ('github_trending','aliyun_solutions','huawei_solutions','ai_app_official')
          AND schedule->>'task_key' IS NULL""")


def downgrade() -> None:
    op.execute("""UPDATE intelligence_sources source SET schedule=
        CASE WHEN source.schedule->>'task_key' = CASE source.source_key
                WHEN 'github_trending' THEN 'github_daily'
                WHEN 'aliyun_solutions' THEN 'solution_catalogs_daily'
                WHEN 'huawei_solutions' THEN 'solution_catalogs_daily'
                WHEN 'ai_app_official' THEN 'ai_applications_daily' END
            THEN CASE WHEN backup.schedule->>'task_key' IS NULL THEN source.schedule-'task_key'
                      ELSE jsonb_set(source.schedule,'{task_key}',backup.schedule->'task_key') END
            ELSE source.schedule END,
        updated_at=NOW()
        FROM insight_migration_f5_source_schedule_backup backup
        WHERE source.source_key=backup.source_key""")
    op.execute("""UPDATE intelligence_sources source SET schedule=
        CASE WHEN source.schedule->>'timezone'='Asia/Shanghai' AND backup.schedule->>'timezone' IS NULL
            THEN source.schedule-'timezone' ELSE source.schedule END,
        updated_at=NOW()
        FROM insight_migration_f5_source_schedule_backup backup
        WHERE source.source_key=backup.source_key""")
    op.execute("DROP TABLE insight_migration_f5_source_schedule_backup")
