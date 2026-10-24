"""Use the stored community endpoints in the community collector."""
from alembic import op

revision = "f4a5b6c7d8e9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""UPDATE intelligence_sources SET base_url='https://top.baidu.com/board?tab=realtime',updated_at=NOW()
        WHERE source_key='community_baidu' AND base_url='https://top.baidu.com/'""")
    op.execute("""UPDATE intelligence_sources SET base_url='https://blog.csdn.net/phoenix/web/blog/hotRank?page=0&pageSize=30',updated_at=NOW()
        WHERE source_key='community_csdn' AND base_url='https://blog.csdn.net/phoenix/web/blog/hotRank'""")


def downgrade() -> None:
    op.execute("""UPDATE intelligence_sources SET base_url='https://top.baidu.com/',updated_at=NOW()
        WHERE source_key='community_baidu' AND base_url='https://top.baidu.com/board?tab=realtime'""")
    op.execute("""UPDATE intelligence_sources SET base_url='https://blog.csdn.net/phoenix/web/blog/hotRank',updated_at=NOW()
        WHERE source_key='community_csdn' AND base_url='https://blog.csdn.net/phoenix/web/blog/hotRank?page=0&pageSize=30'""")
