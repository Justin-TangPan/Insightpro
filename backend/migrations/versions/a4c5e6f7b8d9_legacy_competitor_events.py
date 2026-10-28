"""Preserve already-public legacy competitor notices as source-backed Events."""
from alembic import op
from psycopg2.extras import RealDictCursor

from services.intelligence_data_service import store_competitor_news

revision = "a4c5e6f7b8d9"
down_revision = "a3c4e5f6b7d8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    cursor = op.get_bind().connection.cursor(cursor_factory=RealDictCursor)
    cursor.execute("""SELECT DISTINCT ON (link,title,summary,published_date,category,vendor)
        link AS url,title,summary,published_date,category,vendor,created_at
        FROM competitor_news
        WHERE link ~* '^https?://[^/[:space:]]+' AND title IS NOT NULL AND title<>''
        ORDER BY link,title,summary,published_date,category,vendor,created_at,id""")
    rows = cursor.fetchall()
    event_ids = set()
    for row in sorted(rows, key=lambda item: (str(item["created_at"] or item["published_date"] or ""), item["url"])):
        event_id = store_competitor_news(cursor, dict(row))
        if event_id:
            event_ids.add(event_id)
    if event_ids:
        # These notices were already public through the legacy endpoint; preserve that publication state.
        cursor.execute("""UPDATE intelligence_events SET status='active'
            WHERE id=ANY(%s) AND status='pending_review'""", (list(event_ids),))
    cursor.close()


def downgrade() -> None:
    # Imported evidence and its Event links are historical records and must not be deleted on rollback.
    pass