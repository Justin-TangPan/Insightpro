"""Group immutable historical evidence under stable source objects."""
from alembic import op
import sqlalchemy as sa

revision = "a3c4e5f6b7d8"
down_revision = "a2c3e4f5b6d7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""INSERT INTO intelligence_sources(source_key,name,adapter,base_url,business_scopes,authority)
        VALUES ('competitor_news','友商官方动态','competitor_news',NULL,ARRAY['competitor_dynamics'],'P1')
        ON CONFLICT (source_key) DO NOTHING""")
    op.create_table("intelligence_source_objects",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("source_key", sa.Text(), sa.ForeignKey("intelligence_sources.source_key"), nullable=False),
        sa.Column("identity_key", sa.Text(), nullable=False),
        sa.Column("external_native_id", sa.Text()),
        sa.Column("canonical_url", sa.Text()),
        sa.Column("current_raw_id", sa.BigInteger()),
        sa.Column("current_version", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("migration_status", sa.Text(), nullable=False, server_default="resolved"),
        sa.Column("version_order_uncertain", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_key", "identity_key", name="uq_intelligence_source_object_identity"))
    op.add_column("intelligence_raw_items", sa.Column("source_object_id", sa.BigInteger(), sa.ForeignKey("intelligence_source_objects.id")))
    op.add_column("intelligence_raw_items", sa.Column("source_version", sa.Integer()))
    op.create_index("idx_intelligence_raw_source_object", "intelligence_raw_items", ["source_object_id", "source_version"], unique=True)
    op.create_foreign_key("fk_source_object_current_raw", "intelligence_source_objects", "intelligence_raw_items",
                          ["current_raw_id"], ["id"], ondelete="SET NULL")
    # A missing URL stays unresolved; GitHub ranking periods and metadata are separate source objects.
    op.execute("""CREATE TEMP TABLE _source_object_backfill ON COMMIT DROP AS
        SELECT id,source_key,canonical_url,observed_at,
               CASE WHEN canonical_url ~* '^https?://[^/[:space:]]+' THEN
                    canonical_url || CASE WHEN source_key='github_trending' THEN
                        '#raw=' || COALESCE(content->>'kind',content->>'category','unknown') ELSE '' END
                    ELSE 'unresolved:raw:' || id END AS identity_key,
               CASE WHEN canonical_url ~* '^https?://[^/[:space:]]+' THEN 'resolved' ELSE 'unresolved' END AS migration_status
        FROM intelligence_raw_items""")
    op.execute("""INSERT INTO intelligence_source_objects
        (source_key,identity_key,canonical_url,migration_status,first_seen_at,last_seen_at)
        SELECT source_key,identity_key,
               CASE WHEN migration_status='resolved' THEN MIN(canonical_url) END,
               migration_status,MIN(observed_at),MAX(observed_at)
        FROM _source_object_backfill GROUP BY source_key,identity_key,migration_status""")
    op.execute("""WITH ranked AS (
        SELECT raw.id, obj.id AS object_id,
               row_number() OVER (PARTITION BY obj.id ORDER BY raw.observed_at,raw.id) AS version,
               count(*) OVER (PARTITION BY obj.id,raw.observed_at) > 1 AS uncertain
        FROM intelligence_raw_items raw JOIN _source_object_backfill identity ON identity.id=raw.id
        JOIN intelligence_source_objects obj ON obj.source_key=identity.source_key AND obj.identity_key=identity.identity_key)
        UPDATE intelligence_raw_items raw SET source_object_id=ranked.object_id,source_version=ranked.version
        FROM ranked WHERE raw.id=ranked.id""")
    op.execute("""WITH ranked AS (
        SELECT raw.source_object_id,raw.id,raw.source_version,raw.observed_at,
               row_number() OVER (PARTITION BY raw.source_object_id ORDER BY raw.observed_at DESC,raw.id DESC) AS position
        FROM intelligence_raw_items raw), uncertain AS (
        SELECT source_object_id FROM intelligence_raw_items GROUP BY source_object_id,observed_at HAVING COUNT(*)>1)
        UPDATE intelligence_source_objects obj SET
            current_raw_id=CASE WHEN uncertain.source_object_id IS NULL THEN ranked.id END,
            current_version=ranked.source_version,
            version_order_uncertain=uncertain.source_object_id IS NOT NULL,
            migration_status=CASE WHEN uncertain.source_object_id IS NOT NULL THEN 'unresolved' ELSE obj.migration_status END
        FROM ranked LEFT JOIN (SELECT DISTINCT source_object_id FROM uncertain) uncertain
          ON uncertain.source_object_id=ranked.source_object_id
        WHERE ranked.source_object_id=obj.id AND ranked.position=1""")
    op.alter_column("intelligence_raw_items", "source_object_id", nullable=False)
    op.alter_column("intelligence_raw_items", "source_version", nullable=False)
    op.execute("DROP TRIGGER intelligence_raw_track_change ON intelligence_raw_items")
    op.execute("DROP FUNCTION intelligence_raw_track_change()")
    op.execute("""CREATE FUNCTION intelligence_raw_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF ROW(NEW.source_key,NEW.external_id,NEW.canonical_url,NEW.title,NEW.content,NEW.content_hash,
             NEW.published_at,NEW.observed_at,NEW.source_object_id,NEW.source_version,NEW.content_version,NEW.content_updated_at)
         IS DISTINCT FROM ROW(OLD.source_key,OLD.external_id,OLD.canonical_url,OLD.title,OLD.content,OLD.content_hash,
                              OLD.published_at,OLD.observed_at,OLD.source_object_id,OLD.source_version,OLD.content_version,OLD.content_updated_at) THEN
        RAISE EXCEPTION 'Raw evidence is immutable';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER intelligence_raw_immutable BEFORE UPDATE ON intelligence_raw_items FOR EACH ROW EXECUTE FUNCTION intelligence_raw_immutable()")
    op.execute("""CREATE FUNCTION intelligence_source_object_check_current() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.current_raw_id IS NOT NULL AND NOT EXISTS (
          SELECT 1 FROM intelligence_raw_items WHERE id=NEW.current_raw_id
            AND source_object_id=NEW.id AND source_version=NEW.current_version) THEN
        RAISE EXCEPTION 'Current Raw does not belong to Source Object';
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER intelligence_source_object_check_current BEFORE UPDATE ON intelligence_source_objects FOR EACH ROW EXECUTE FUNCTION intelligence_source_object_check_current()")


def downgrade() -> None:
    op.execute("DROP TRIGGER intelligence_source_object_check_current ON intelligence_source_objects")
    op.execute("DROP FUNCTION intelligence_source_object_check_current()")
    op.execute("DROP TRIGGER intelligence_raw_immutable ON intelligence_raw_items")
    op.execute("DROP FUNCTION intelligence_raw_immutable()")
    op.execute("""CREATE FUNCTION intelligence_raw_track_change() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.content_hash IS DISTINCT FROM OLD.content_hash OR NEW.title IS DISTINCT FROM OLD.title
         OR NEW.canonical_url IS DISTINCT FROM OLD.canonical_url OR NEW.published_at IS DISTINCT FROM OLD.published_at THEN
        NEW.content_version := OLD.content_version + 1;
        NEW.content_updated_at := NOW();
        INSERT INTO intelligence_raw_changes(raw_item_id,old_hash,new_hash,content_version)
        VALUES (OLD.id,OLD.content_hash,NEW.content_hash,NEW.content_version);
      ELSE
        NEW.content_version := OLD.content_version;
        NEW.content_updated_at := OLD.content_updated_at;
      END IF;
      NEW.last_seen_at := NOW();
      RETURN NEW;
    END $$""")
    op.execute("CREATE TRIGGER intelligence_raw_track_change BEFORE UPDATE ON intelligence_raw_items FOR EACH ROW EXECUTE FUNCTION intelligence_raw_track_change()")
    op.drop_constraint("fk_source_object_current_raw", "intelligence_source_objects")
    op.drop_index("idx_intelligence_raw_source_object", table_name="intelligence_raw_items")
    op.drop_column("intelligence_raw_items", "source_version")
    op.drop_column("intelligence_raw_items", "source_object_id")
    op.drop_table("intelligence_source_objects")
