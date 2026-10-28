"""Track raw evidence changes without duplicating source items."""
from alembic import op
import sqlalchemy as sa

revision = "d6e7f8a9b0c1"
down_revision = "c5d6e7f8a9b0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("intelligence_raw_items", sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("intelligence_raw_items", sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.add_column("intelligence_raw_items", sa.Column("content_updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.execute("UPDATE intelligence_raw_items SET last_seen_at=observed_at, content_updated_at=observed_at")
    op.create_table("intelligence_raw_changes",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("raw_item_id", sa.BigInteger(), sa.ForeignKey("intelligence_raw_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("old_hash", sa.Text()), sa.Column("new_hash", sa.Text()),
        sa.Column("content_version", sa.Integer(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()))
    op.execute("""CREATE FUNCTION intelligence_raw_track_change() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.content_hash IS DISTINCT FROM OLD.content_hash OR NEW.title IS DISTINCT FROM OLD.title
         OR NEW.canonical_url IS DISTINCT FROM OLD.canonical_url
         OR NEW.published_at IS DISTINCT FROM OLD.published_at THEN
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
    op.execute("""CREATE TRIGGER intelligence_raw_track_change BEFORE UPDATE ON intelligence_raw_items
        FOR EACH ROW EXECUTE FUNCTION intelligence_raw_track_change()""")


def downgrade() -> None:
    op.execute("DROP TRIGGER intelligence_raw_track_change ON intelligence_raw_items")
    op.execute("DROP FUNCTION intelligence_raw_track_change()")
    op.drop_table("intelligence_raw_changes")
    op.drop_column("intelligence_raw_items", "content_updated_at")
    op.drop_column("intelligence_raw_items", "last_seen_at")
    op.drop_column("intelligence_raw_items", "content_version")
