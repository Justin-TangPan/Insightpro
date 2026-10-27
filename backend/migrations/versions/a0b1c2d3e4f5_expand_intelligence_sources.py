"""Extend the existing source registry with public and official discovery feeds."""
from alembic import op
import sqlalchemy as sa

revision = "a0b1c2d3e4f5"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None

SOURCES = (
    ("hacker_news", "Hacker News", "hacker_news_api", "https://hn.algolia.com/api/v1/search?tags=front_page", "COMMUNITY", "en", "GLOBAL", "technology_ecosystem,ai_applications,community_insights,competitor_dynamics"),
    ("hugging_face", "Hugging Face Models", "hugging_face_api", "https://huggingface.co/api/models", "PLATFORM", "en", "GLOBAL", "technology_ecosystem,ai_applications"),
    ("arxiv_ai", "arXiv AI Research", "arxiv_api", "https://export.arxiv.org/api/query", "ACADEMIC", "en", "GLOBAL", "technology_ecosystem"),
    ("techcrunch_ai", "TechCrunch AI", "rss_feed", "https://techcrunch.com/category/artificial-intelligence/feed/", "MEDIA", "en", "GLOBAL", "technology_ecosystem,ai_applications,competitor_dynamics"),
    ("infoq_cn", "InfoQ 中国", "rss_feed", "https://www.infoq.cn/feed", "MEDIA", "zh", "CN", "technology_ecosystem,ai_applications,community_insights"),
    ("oschina", "开源中国", "rss_feed", "https://www.oschina.net/news/rss", "COMMUNITY", "zh", "CN", "technology_ecosystem,community_insights"),
    ("solidot", "Solidot", "rss_feed", "https://www.solidot.org/index.rss", "MEDIA", "zh", "CN", "technology_ecosystem,community_insights"),
    ("qbitai", "量子位", "rss_feed", "https://www.qbitai.com/tag/ai/feed", "MEDIA", "zh", "CN", "technology_ecosystem,ai_applications,community_insights"),
    ("leiphone", "雷锋网", "rss_feed", "https://www.leiphone.com/feed", "MEDIA", "zh", "CN", "technology_ecosystem,ai_applications,competitor_dynamics"),
    ("geekpark", "极客公园", "rss_feed", "https://www.geekpark.net/rss", "MEDIA", "zh", "CN", "ai_applications,community_insights,competitor_dynamics"),
    ("tmtpost", "钛媒体", "rss_feed", "https://www.tmtpost.com/feed", "MEDIA", "zh", "CN", "ai_applications,competitor_dynamics"),
    ("unite_ai", "Unite AI", "rss_feed", "https://www.unite.ai/feed/", "MEDIA", "en", "GLOBAL", "technology_ecosystem,ai_applications,competitor_dynamics"),
    ("ifanr", "爱范儿", "rss_feed", "https://www.ifanr.com/feed", "MEDIA", "zh", "CN", "ai_applications,community_insights"),
    ("sspai", "少数派", "rss_feed", "https://sspai.com/feed", "COMMUNITY", "zh", "CN", "ai_applications,community_insights"),
    ("aws_ai_blog", "AWS AI Blog", "rss_feed", "https://aws.amazon.com/blogs/machine-learning/feed/", "OFFICIAL", "en", "GLOBAL", "technology_ecosystem,ai_applications,competitor_dynamics"),
    ("azure_updates", "Azure Updates", "rss_feed", "https://www.microsoft.com/releasecommunications/api/v2/azure/rss", "OFFICIAL", "en", "GLOBAL", "technology_ecosystem,ai_applications,competitor_dynamics"),
    ("azure_foundry", "Azure AI Foundry", "rss_feed", "https://devblogs.microsoft.com/foundry/feed/", "OFFICIAL", "en", "GLOBAL", "technology_ecosystem,ai_applications,competitor_dynamics"),
    ("google_cloud_ai", "Google Cloud AI Blog", "html_links", "https://cloud.google.com/blog/products/ai-machine-learning", "OFFICIAL", "en", "GLOBAL", "technology_ecosystem,ai_applications,competitor_dynamics"),
    ("huawei_cloud_news", "Huawei Cloud News", "html_links", "https://www.huaweicloud.com/intl/en-us/news", "OFFICIAL", "en", "GLOBAL", "competitor_dynamics,ai_applications"),
    ("baidu_ai_cloud", "百度智能云产品动态", "html_links", "https://cloud.baidu.com/news/productNews", "OFFICIAL", "zh", "CN", "ai_applications,competitor_dynamics"),
)

KEYWORDS = (
    ("大模型", "大模型", "zh"), ("大模型", "large language model", "en"), ("大模型", "llm", "en"),
    ("智能体", "智能体", "zh"), ("智能体", "agentic", "en"), ("智能体", "ai agent", "en"), ("智能体", "agent", "en"),
    ("推理部署", "推理", "zh"), ("推理部署", "inference", "en"), ("推理部署", "部署", "zh"),
    ("训练微调", "微调", "zh"), ("训练微调", "fine-tuning", "en"), ("训练微调", "training", "en"),
    ("多模态", "多模态", "zh"), ("多模态", "multimodal", "en"),
    ("RAG", "rag", "en"), ("RAG", "知识库", "zh"),
    ("代码AI", "code assistant", "en"), ("代码AI", "代码助手", "zh"),
    ("基础设施", "ai infrastructure", "en"), ("基础设施", "算力", "zh"),
    ("安全合规", "ai safety", "en"), ("安全合规", "人工智能安全", "zh"),
    ("具身智能", "具身智能", "zh"), ("具身智能", "robotics", "en"),
    ("模型评测", "benchmark", "en"), ("模型评测", "模型评测", "zh"),
    ("工作流", "workflow", "en"), ("工作流", "工作流", "zh"),
    ("开源生态", "open source ai", "en"), ("开源生态", "开源模型", "zh"),
    ("MCP", "mcp", "en"), ("MCP", "工具调用", "zh"),
    ("AI应用", "ai app", "en"), ("AI应用", "ai应用", "zh"),
    ("企业AI", "enterprise ai", "en"), ("企业AI", "企业ai", "zh"),
    ("商业化成本", "token cost", "en"), ("商业化成本", "商业化", "zh"),
    ("通用", "人工智能", "zh"), ("通用", "artificial intelligence", "en"),
    ("通用", "gemini", "en"), ("通用", "claude", "en"), ("通用", "openai", "en"),
    ("通用", "deepseek", "en"), ("通用", "copilot", "en"),
)


def upgrade():
    for name, kind in (("source_role", "TEXT NOT NULL DEFAULT 'PLATFORM'"), ("language", "TEXT NOT NULL DEFAULT 'zh'"),
                       ("region", "TEXT NOT NULL DEFAULT 'CN'"), ("last_run_at", "TIMESTAMPTZ"),
                       ("last_new_count", "INTEGER NOT NULL DEFAULT 0"), ("consecutive_failures", "INTEGER NOT NULL DEFAULT 0"),
                       ("total_runs", "INTEGER NOT NULL DEFAULT 0"), ("successful_runs", "INTEGER NOT NULL DEFAULT 0")):
        op.execute(f"ALTER TABLE intelligence_sources ADD COLUMN {name} {kind}")
    op.execute("""UPDATE intelligence_sources SET source_role=CASE
        WHEN source_key='arxiv_ai' THEN 'ACADEMIC' WHEN source_key='hacker_news' THEN 'COMMUNITY'
        WHEN source_key IN ('github_trending','github_search','hugging_face','product_hunt') THEN 'PLATFORM'
        WHEN adapter IN ('competitor_news','ai_applications_official') THEN 'OFFICIAL' ELSE 'COMMUNITY' END,
        language=CASE WHEN source_key IN ('hacker_news','arxiv_ai','hugging_face','github_search','product_hunt') THEN 'en' ELSE 'zh' END
        WHERE NOT ('solutions'=ANY(business_scopes))""")
    op.execute("""UPDATE intelligence_sources SET base_url='https://hn.algolia.com/api/v1/search?tags=front_page',
        business_scopes=ARRAY['technology_ecosystem','ai_applications','community_insights','competitor_dynamics']
        WHERE source_key='hacker_news'""")
    op.create_table("intelligence_topic_keywords", sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("topic", sa.Text(), nullable=False), sa.Column("keyword", sa.Text(), nullable=False),
        sa.Column("language", sa.Text(), nullable=False), sa.Column("type", sa.Text(), nullable=False, server_default="INCLUDE"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("topic", "keyword", "type"), sa.CheckConstraint("type IN ('INCLUDE','EXCLUDE')"))
    bind = op.get_bind()
    for topic, keyword, language in KEYWORDS:
        bind.execute(sa.text("INSERT INTO intelligence_topic_keywords(topic,keyword,language) VALUES (:t,:k,:l)"), {"t": topic, "k": keyword, "l": language})
    bind.execute(sa.text("INSERT INTO intelligence_topic_keywords(topic,keyword,language,type) VALUES ('智能体','travel agent','en','EXCLUDE'),('智能体','user agent','en','EXCLUDE')"))
    for key, name, adapter, url, role, language, region, scopes in SOURCES:
        bind.execute(sa.text("""INSERT INTO intelligence_sources
            (source_key,name,adapter,base_url,business_scopes,authority,priority,schedule,enabled,source_role,language,region)
            VALUES (:key,:name,:adapter,:url,string_to_array(:scopes,','),:authority,80,
            '{"task_key":"discovery_sentinel_daily","cron":"45 8 * * *","timezone":"Asia/Shanghai"}'::jsonb,
            TRUE,:role,:language,:region) ON CONFLICT (source_key) DO NOTHING"""),
            {"key": key, "name": name, "adapter": adapter, "url": url, "scopes": scopes,
             "authority": "P0" if role == "OFFICIAL" else "P1", "role": role, "language": language, "region": region})


def downgrade():
    op.drop_table("intelligence_topic_keywords")
    for column in ("source_role", "language", "region", "last_run_at", "last_new_count", "consecutive_failures", "total_runs", "successful_runs"):
        op.execute(f"ALTER TABLE intelligence_sources DROP COLUMN {column}")
