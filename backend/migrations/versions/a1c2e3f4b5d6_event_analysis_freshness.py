"""Invalidate event analysis when its evidence changes."""
from alembic import op
import sqlalchemy as sa

revision = "a1c2e3f4b5d6"
down_revision = "d6e7f8a9b0c1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("intelligence_events", sa.Column("content_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("intelligence_events", sa.Column("analysis_version", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("intelligence_events", sa.Column("analysis_status", sa.Text(), nullable=False, server_default="stale"))
    op.create_check_constraint("ck_event_analysis_status", "intelligence_events",
                               "analysis_status IN ('fresh','stale','processing','failed')")
    # Existing AI payloads have no evidence-version record; keep them visible but require reanalysis before reuse.
    op.execute("""CREATE FUNCTION intelligence_event_evidence_changed() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      UPDATE intelligence_events SET content_version=content_version+1,analysis_status='stale',updated_at=NOW()
      WHERE id=COALESCE(NEW.event_id,OLD.event_id);
      RETURN COALESCE(NEW,OLD);
    END $$""")
    op.execute("""CREATE TRIGGER intelligence_event_evidence_insert AFTER INSERT ON intelligence_event_evidence
        FOR EACH ROW EXECUTE FUNCTION intelligence_event_evidence_changed()""")
    op.execute("""CREATE TRIGGER intelligence_event_evidence_delete AFTER DELETE ON intelligence_event_evidence
        FOR EACH ROW EXECUTE FUNCTION intelligence_event_evidence_changed()""")
    op.execute("""CREATE FUNCTION intelligence_event_raw_changed() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN
      IF NEW.content_version > OLD.content_version THEN
        UPDATE intelligence_events SET content_version=content_version+1, analysis_status='stale', updated_at=NOW()
        WHERE id IN (SELECT event_id FROM intelligence_event_evidence WHERE raw_item_id=NEW.id);
      END IF;
      RETURN NEW;
    END $$""")
    op.execute("""CREATE TRIGGER intelligence_event_raw_update AFTER UPDATE ON intelligence_raw_items
        FOR EACH ROW EXECUTE FUNCTION intelligence_event_raw_changed()""")


def downgrade() -> None:
    op.execute("DROP TRIGGER intelligence_event_raw_update ON intelligence_raw_items")
    op.execute("DROP FUNCTION intelligence_event_raw_changed()")
    op.execute("DROP TRIGGER intelligence_event_evidence_delete ON intelligence_event_evidence")
    op.execute("DROP TRIGGER intelligence_event_evidence_insert ON intelligence_event_evidence")
    op.execute("DROP FUNCTION intelligence_event_evidence_changed()")
    op.drop_constraint("ck_event_analysis_status", "intelligence_events")
    op.drop_column("intelligence_events", "analysis_status")
    op.drop_column("intelligence_events", "analysis_version")
    op.drop_column("intelligence_events", "content_version")
