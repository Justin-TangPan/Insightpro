"""Seed the managed repository business evaluation prompt."""
from alembic import op

revision = "a9b0c1d2e3f4"
down_revision = "f4a5b6c7d8e9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO intelligence_prompts
          (prompt_name,scenario,version,status,system_prompt,user_prompt_template)
        VALUES (
          'repository_business_eval','business_impact',1,'published',
          'You evaluate the business and solution value of open-source repositories. Use only the supplied repository evidence. Do not invent users, product capabilities, adoption, market share, release history, metrics, or customer outcomes. Score four dimensions from 0 to 10: D1 customer pain and urgency; D2 scenario fit and customer coverage; D3 business value and justified cloud consumption; D4 engineering maturity, deployability, and repeatable delivery. Total is the average of the four scores, rounded to one decimal. If D1 or D2 is below 4, or no credible customer scenario and repeatable delivery path is supported, cap total at 5.9. Pure desktop tools, browser extensions, standalone scripts, and algorithm libraries are generally not recommended. Levels: 8-10 Strongly Recommended; 6-7.9 Worth Doing; 4-5.9 Marginal; 0-3.9 Not Recommended. Return only a JSON array. Each element must contain repo_name, summary, d1, d2, d3, d4, total, level, recommendation, reasoning. Write all text fields in Simplified Chinese; recommendation must name concrete validation steps.',
          'Evaluate the following repositories using only the evidence below. Return a JSON array with repo_name, summary, d1, d2, d3, d4, total, level, recommendation, reasoning.\n\n{projects}'
        )
        ON CONFLICT (prompt_name,version) DO NOTHING
    """)


def downgrade() -> None:
    pass
