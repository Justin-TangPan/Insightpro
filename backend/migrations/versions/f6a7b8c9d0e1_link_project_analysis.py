"""Link every dated project sighting to its canonical AI analysis."""
from alembic import op
import sqlalchemy as sa

revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("trending_business_eval", sa.Column("analysis_id", sa.Integer(), sa.ForeignKey("trending_business_eval.id")))
    op.execute("""WITH canonical AS (
                    SELECT DISTINCT ON (repo_name) repo_name, id
                    FROM trending_business_eval
                    WHERE reasoning IS NOT NULL AND reasoning <> ''
                      AND reasoning NOT IN (
                        'AI 不可用时，按客户痛点、场景适配、业务与云价值、标准化交付进行临时解决方案价值评估。',
                        'When AI is unavailable, generate a temporary evaluation based on server-side attributes, independent deployment needs, scenario value, and standardization & reproducibility.'
                      )
                    ORDER BY repo_name, scrape_date, id
                  )
                  UPDATE trending_business_eval e SET analysis_id=canonical.id
                  FROM canonical WHERE e.repo_name=canonical.repo_name""")


def downgrade() -> None:
    op.drop_column("trending_business_eval", "analysis_id")
