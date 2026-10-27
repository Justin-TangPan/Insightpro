"""Persist homepage email content for preview, history, and retry."""
from alembic import op
import sqlalchemy as sa

revision = 'e4f5a6b7c8d9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('email_content_snapshots',
        sa.Column('id', sa.Text(), primary_key=True),
        sa.Column('language', sa.Text(), nullable=False),
        sa.Column('homepage_data', sa.JSON(), nullable=False),
        sa.Column('html', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.add_column('email_delivery_attempts', sa.Column('snapshot_id', sa.Text(), sa.ForeignKey('email_content_snapshots.id')))


def downgrade():
    op.drop_column('email_delivery_attempts', 'snapshot_id')
    op.drop_table('email_content_snapshots')
