"""
DeepSearcher Integration Module for InsightPro
===============================================
Integrates zilliztech/deep-searcher as the core retrieval engine.
Replaces all direct DeepSeek API calls with RAG-powered search and reasoning.

Architecture:
  - Vector DB: Qdrant local (file-based, no server)
  - Embedding: SentenceTransformer (BAAI/bge-m3, local, multilingual)
  - LLM: DeepSeek (via existing API key)
  - Retrieval: DeepSearch + ChainOfRAG agents via RAGRouter
"""

import os
import sys
import sqlite3
import json
import logging
from typing import List, Optional, Tuple
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from dotenv import load_dotenv

load_dotenv(dotenv_path="../.env", override=True)

logger = logging.getLogger("deep-searcher")
# Suppress verbose dev logger from deepsearcher
logging.getLogger("dev").setLevel(logging.ERROR)
logging.getLogger("deepsearcher").setLevel(logging.ERROR)
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)

# ──────────────────────────────────────────────
# Monkey-patch: Ensure firecrawl compatibility
# ──────────────────────────────────────────────
import importlib.util
_firecrawl_spec = importlib.util.find_spec("firecrawl")
if _firecrawl_spec is not None:
    import firecrawl
    if not hasattr(firecrawl, "ScrapeOptions"):
        # Create compatibility alias for newer firecrawl versions
        if hasattr(firecrawl, "V1ScrapeOptions"):
            firecrawl.ScrapeOptions = firecrawl.V1ScrapeOptions
            logger.info("Monkey-patched firecrawl.ScrapeOptions → V1ScrapeOptions")

# ──────────────────────────────────────────────
# DeepSearcher Imports
# ──────────────────────────────────────────────
from deepsearcher.configuration import Configuration, init_config
from deepsearcher.online_query import query as ds_query, retrieve as ds_retrieve
from deepsearcher.offline_loading import load_from_local_files
from deepsearcher.embedding.sentence_transformer_embedding import SentenceTransformerEmbedding
from deepsearcher.loader.splitter import Chunk, split_docs_to_chunks
from deepsearcher.vector_db.base import RetrievalResult
from langchain_core.documents import Document
from deepsearcher.utils import log as ds_log

# Disable deepsearcher's extremely verbose dev logger
ds_log.dev_logger.disabled = True

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
DB_PATH = os.path.join(os.path.dirname(__file__), "trending.db")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY")
DEEPSEEK_API_BASE = os.getenv("DEEPSEEK_API_BASE", "https://api.deepseek.com")
# Using Qdrant in-memory mode (no server needed, persists to disk)
QDRANT_PATH = os.path.join(os.path.dirname(__file__), "deep_searcher_qdrant")

# Collection names
COLL_PLATFORM = "platform_knowledge"
COLL_DEMAND = "demand_signals"
COLL_COMPETITOR = "competitive_news"
COLL_GITHUB = "github_trending"
COLL_POLICY = "policies"

ALL_COLLECTIONS = [COLL_PLATFORM, COLL_DEMAND, COLL_COMPETITOR, COLL_GITHUB, COLL_POLICY]

_is_initialized = False

# ──────────────────────────────────────────────
# Initialization
# ──────────────────────────────────────────────
def init_deep_searcher(force_reload: bool = False):
    """
    Initialize DeepSearcher with our configuration.
    - LLM: DeepSeek
    - Embedding: SentenceTransformer (bge-base-zh-v1.5) — local, Chinese-optimized
    - Vector DB: Milvus Lite (file-based)

    Args:
        force_reload: If True, drop all existing collections and reload data.
    """
    global _is_initialized

    if _is_initialized and not force_reload:
        logger.info("DeepSearcher already initialized, skipping")
        return

    logger.info("Initializing DeepSearcher...")

    # Create configuration
    config = Configuration()

    # Set LLM → DeepSeek
    config.set_provider_config("llm", "DeepSeek", {
        "model": "deepseek-chat",
        "api_key": DEEPSEEK_API_KEY,
        "base_url": DEEPSEEK_API_BASE,
    })

    # Set Embedding → SentenceTransformer (local, multilingual)
    # bge-m3 supports Chinese + English, 1024 dims
    config.set_provider_config("embedding", "SentenceTransformerEmbedding", {
        "model": "BAAI/bge-m3",
    })

    # Set File Loader → TextLoader (simple text file loading)
    config.set_provider_config("file_loader", "TextLoader", {})

    # Set Web Crawler → JinaCrawler (won't be used, but needs a valid provider)
    # Set dummy env var since we never actually crawl websites
    if not os.environ.get("JINA_API_TOKEN"):
        os.environ["JINA_API_TOKEN"] = "dummy-token-not-used"
    config.set_provider_config("web_crawler", "JinaCrawler", {})

    # Set Vector DB → Qdrant local (persisted to disk, no server needed)
    config.set_provider_config("vector_db", "Qdrant", {
        "default_collection": "deepsearcher",
        "path": QDRANT_PATH,
    })

    # Initialize modules
    init_config(config=config)

    _is_initialized = True
    logger.info(f"DeepSearcher initialized. Qdrant path: {QDRANT_PATH}")

    # Load data (skip if already loaded)
    _load_all_data(reload=force_reload)


def _load_all_data(reload: bool = False):
    """
    Load all existing data from SQLite into vector DB collections.
    Each data type gets its own collection for targeted retrieval.
    """
    from deepsearcher import configuration as ds_config
    vector_db = ds_config.vector_db
    embedding_model = ds_config.embedding_model
    dim = embedding_model.dimension

    if reload:
        try:
            for coll in ALL_COLLECTIONS:
                vector_db.init_collection(dim=dim, collection=coll, description=coll, force_new_collection=True)
            logger.info("All collections re-created")
        except Exception as e:
            logger.warning(f"Could not force-recreate collections: {e}")

    # Skip loading if collections already have data (fast restart)
    try:
        existing_count = sum(vector_db.client.count(collection_name=coll) for coll in ALL_COLLECTIONS if hasattr(vector_db.client, 'count'))
    except Exception:
        existing_count = 0

    if existing_count > 0 and not reload:
        logger.info(f"Collections already have {existing_count} points, skipping data load")
        return

    # Load platform knowledge
    _load_platform_knowledge(vector_db, embedding_model)

    # Load demand signals
    _load_demand_signals(vector_db, embedding_model)

    # Load competitor news
    _load_competitor_news(vector_db, embedding_model)

    # Load GitHub trending
    _load_github_trending(vector_db, embedding_model)

    # Load policies (extracted from demand signal policies)
    _load_policies(vector_db, embedding_model)

    logger.info("All data loaded into vector DB")


def _documents_to_chunks(docs: List[Document], embedding_model, vector_db, collection: str,
                          dim: int, chunk_size: int = 800, chunk_overlap: int = 100):
    """Helper: convert Document list → chunks → embed → insert into collection."""
    # Init collection if needed
    try:
        vector_db.init_collection(dim=dim, collection=collection, description=collection, force_new_collection=False)
    except Exception:
        pass  # Collection already exists

    if not docs:
        logger.info(f"No documents for collection '{collection}', skipping")
        return

    chunks = split_docs_to_chunks(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    chunks = embedding_model.embed_chunks(chunks, batch_size=32)
    vector_db.insert_data(collection=collection, chunks=chunks)
    logger.info(f"Loaded {len(chunks)} chunks into '{collection}'")


def _load_platform_knowledge(vector_db, embedding_model):
    """Load the platform's knowledge base (KNOWLEDGE_BASE text) into vector DB."""
    from deepsearcher import configuration as ds_config
    dim = embedding_model.dimension

    knowledge_text = """# InsightPro 商业洞察平台

## 平台概述
InsightPro 是面向云服务商业市场（中长尾、腰部行业客户）业务领导的 AI 驱动商业洞察平台，帮助用户快速获取行业动态、竞争分析、政策法规和市场机会。

## 核心功能模块
1. **今日洞察**（首页）：每日商业简报入口，展示 6 大板块摘要
2. **行业全景**（/insights/industry）：覆盖生物医疗、交通、基础设施、互联网、零售、制造 6 大行业，每个行业含具体客户案例和厂商方案
3. **案例库**（/insights/industry/cases）：5 大行业深度案例（三一重工、省级医疗集团、省会城市交通、农商行信创、连锁便利店），含友商对比和数据来源
4. **技术热点**（/insights/hotspots）：GitHub Trending 实时监控，支持日/周/月维度，历史数据追溯
5. **友商洞察**（/insights/competitors）：6 大场景分析（出海、AI平台、开发者、SaaS、性价比、数字化），对比 AWS/Azure/阿里云/腾讯云/火山云
6. **政策法规**（/insights/policy）：等保 2.0、信创替代、数据出境、OPC、数字化补贴、SOC 6 项政策追踪
7. **商业快讯**（/insights/news）：Reuters/Bloomberg/财新网/Wired 实时新闻
8. **增长机会**（/insights/opportunities）：综合分析页，聚合所有子版块数据形成 6 大机会点
9. **数据大屏**（/dashboard）：KPI 看板 + Recharts 趋势图 + 实时监测
10. **深度研报**（/reports）：AI 生成的结构化商业研报
11. **历史日报**（/history）：GitHub Trending 历史快照，支持搜索

## 技术栈
- 前端：Next.js 14+ / React / TypeScript / Tailwind CSS / Recharts
- 后端：FastAPI / Python / SQLite / APScheduler
- AI：DeepSeek-V3 / ModelArts
- 数据源：GitHub Trending API / 百度热搜爬虫 / 友商动态库

## 邮件订阅
平台支持每日 09:05 自动发送洞察简报邮件，包含友商动态和 GitHub 技术热点。用户可在设置页面管理订阅。

## 目标用户
- 云服务商业市场的业务决策者
- 中长尾客户和腰部客户的销售和市场团队
- 需要了解行业数字化趋势的解决方案架构师
"""

    doc = Document(
        page_content=knowledge_text,
        metadata={"source": "platform_knowledge", "type": "system"}
    )
    _documents_to_chunks([doc], embedding_model, vector_db, COLL_PLATFORM, dim)


def _load_demand_signals(vector_db, embedding_model):
    """Load demand signals from SQLite into vector DB."""
    from deepsearcher import configuration as ds_config
    dim = embedding_model.dimension

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute("SELECT * FROM demand_signals ORDER BY signal_date DESC LIMIT 100")
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()

    if not rows:
        logger.info("No demand signals found in DB, initializing from inline data")
        signals = _get_inline_demand_signals()
    else:
        signals = [dict(r) for r in rows]

    docs = []
    for s in signals:
        text = f"[{s.get('source_type','')}] [{s.get('industry','')}] {s.get('title','')}\n{s.get('summary','')}\n需求标签: {s.get('demand_tags','')}"
        doc = Document(
            page_content=text,
            metadata={
                "source": "demand_signal",
                "type": s.get("source_type", ""),
                "industry": s.get("industry", ""),
                "title": s.get("title", ""),
                "url": s.get("url", ""),
                "relevance_score": s.get("relevance_score", 0.5),
                "tags": s.get("demand_tags", ""),
            }
        )
        docs.append(doc)

    _documents_to_chunks(docs, embedding_model, vector_db, COLL_DEMAND, dim, chunk_size=500)


def _get_inline_demand_signals():
    """Fallback: return inline demand signals if DB is empty."""
    return [
        {"source_type": "policy", "industry": "制造", "title": "工信部发布《制造业数字化转型行动方案（2026-2028）》", "summary": "明确要求规模以上制造企业数字化研发设计工具普及率达到 85%，关键工序数控化率达到 72%。", "url": "https://www.miit.gov.cn/", "relevance_score": 0.95, "demand_tags": "工业互联网,智能制造,数字化转型"},
        {"source_type": "policy", "industry": "医疗", "title": "国家卫健委《关于推进医疗机构信息化建设的指导意见》", "summary": "要求三级医院在 2027 年前完成电子病历系统升级改造，二级医院在 2028 年前实现互联互通标准化成熟度测评达标。", "url": "https://www.nhc.gov.cn/", "relevance_score": 0.92, "demand_tags": "医疗信息化,AI诊断,电子病历"},
        {"source_type": "policy", "industry": "政务", "title": "国务院《数字政府建设一体化推进方案》", "summary": "要求省级政务云平台覆盖率 2027 年达到 100%，地市级达到 90%。推动政务数据共享开放。", "url": "https://www.gov.cn/", "relevance_score": 0.93, "demand_tags": "政务云,数据共享,数字政府"},
        {"source_type": "policy", "industry": "金融", "title": "央行《金融科技发展规划（2026-2028）》", "summary": "推进金融基础设施云化改造，要求核心系统分布式改造覆盖率 2028 年达到 60%。", "url": "http://www.pbc.gov.cn/", "relevance_score": 0.90, "demand_tags": "金融云,分布式改造,数据安全"},
        {"source_type": "policy", "industry": "零售", "title": "商务部《关于推动零售业数字化转型的指导意见》", "summary": "支持连锁零售企业建设数字化供应链管理系统，推进线上线下融合发展。", "url": "https://www.mofcom.gov.cn/", "relevance_score": 0.85, "demand_tags": "零售数字化,供应链,AI营销"},
        {"source_type": "bidding", "industry": "政务", "title": "某省会城市政务云平台扩容项目招标（预算 2.8 亿）", "summary": "采购内容包括政务云底座建设、数据中台、AI 中台、安全合规体系。", "url": "http://www.chinabidding.com/", "relevance_score": 0.98, "demand_tags": "政务云,国产化,等保三级"},
        {"source_type": "bidding", "industry": "制造", "title": "某汽车集团工业互联网平台建设项目（预算 1.2 亿）", "summary": "建设覆盖 5 个工厂的工业互联网平台，包括设备联网、数据采集、AI 质检。", "url": "http://www.chinabidding.com/", "relevance_score": 0.96, "demand_tags": "工业互联网,AI质检,设备联网"},
        {"source_type": "bidding", "industry": "医疗", "title": "某省级医疗集团 AI 影像诊断平台采购（预算 8000 万）", "summary": "建设覆盖 20 家医院的 AI 影像诊断平台，支持肺结节、骨折、脑卒中自动识别。", "url": "http://www.chinabidding.com/", "relevance_score": 0.94, "demand_tags": "医疗AI,影像诊断,数据合规"},
        {"source_type": "bidding", "industry": "金融", "title": "某城商行分布式核心系统改造项目（预算 6000 万）", "summary": "将现有 IBM 小型机核心系统迁移至国产分布式架构。", "url": "http://www.chinabidding.com/", "relevance_score": 0.97, "demand_tags": "信创替代,分布式核心,等保四级"},
        {"source_type": "report", "industry": "制造", "title": "IDC：2026 年中国工业互联网市场规模将达 1,500 亿元", "summary": "工业互联网平台从'建平台'转向'用平台'阶段，AI 质检和预测性维护成为最热门应用场景。", "url": "https://www.idc.com/", "relevance_score": 0.88, "demand_tags": "工业互联网,AI质检,中小企业上云"},
        {"source_type": "report", "industry": "医疗", "title": "Frost & Sullivan：中国医疗 AI 市场 2026 年达 500 亿元", "summary": "AI 影像诊断占比最高（42%），AI 药物研发增速最快（+85%）。", "url": "https://www.frostchina.com/", "relevance_score": 0.86, "demand_tags": "医疗AI,影像诊断,数据合规"},
        {"source_type": "report", "industry": "零售", "title": "艾瑞咨询：中国零售数字化市场 2026 年达 5,200 亿元", "summary": "即时零售渗透率突破 50%，AI 驱动的精准营销和智能选品成为零售商核心需求。", "url": "https://www.iresearch.com.cn/", "relevance_score": 0.84, "demand_tags": "零售数字化,AI营销,即时零售"},
        {"source_type": "report", "industry": "政务", "title": "中国信通院：政务云市场 2026 年达 1,200 亿元", "summary": "政务云从 IaaS 向 PaaS/SaaS 升级，AI 中台和数据中台成为新增长点。", "url": "https://www.caict.ac.cn/", "relevance_score": 0.87, "demand_tags": "政务云,AI中台,国产化"},
        {"source_type": "tech_trend", "industry": "通用", "title": "大模型 Agent 化趋势加速，企业级 Agent 平台需求爆发", "summary": "GitHub 上 AI Agent 项目 Star 总数增长 340%，企业对 Agent 编排平台需求快速增长。", "url": "https://github.com/trending", "relevance_score": 0.91, "demand_tags": "AI Agent,MCP协议,企业AI"},
        {"source_type": "tech_trend", "industry": "通用", "title": "边缘计算 + AI 推理成为制造业刚需", "summary": "边缘 AI 推理市场年增 55%，制造企业需要在产线端实现实时质检和预测性维护。", "url": "https://github.com/trending", "relevance_score": 0.89, "demand_tags": "边缘计算,AI推理,端边云协同"},
        {"source_type": "tech_trend", "industry": "通用", "title": "数据安全与隐私计算技术需求激增", "summary": "数据出境法规趋严，企业对隐私计算技术需求增长 120%。", "url": "https://github.com/trending", "relevance_score": 0.87, "demand_tags": "数据安全,隐私计算,合规"},
    ]


def _load_competitor_news(vector_db, embedding_model):
    """Load competitor news from SQLite into vector DB."""
    from deepsearcher import configuration as ds_config
    dim = embedding_model.dimension

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute("SELECT * FROM competitor_news ORDER BY scrape_date DESC LIMIT 30")
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()

    if not rows:
        logger.info("No competitor news found in DB")
        return

    docs = []
    for r in rows:
        d = dict(r)
        text = f"[{d.get('vendor','')}] {d.get('title','')}\n{d.get('summary','')}"
        doc = Document(
            page_content=text,
            metadata={
                "source": "competitor_news",
                "vendor": d.get("vendor", ""),
                "category": d.get("category", ""),
                "link": d.get("link", ""),
                "date": d.get("scrape_date", ""),
            }
        )
        docs.append(doc)

    _documents_to_chunks(docs, embedding_model, vector_db, COLL_COMPETITOR, dim, chunk_size=500)


def _load_github_trending(vector_db, embedding_model):
    """Load GitHub trending repos from SQLite into vector DB."""
    from deepsearcher import configuration as ds_config
    dim = embedding_model.dimension

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        c.execute("SELECT * FROM github_trending ORDER BY scrape_date DESC, stars DESC LIMIT 50")
        rows = c.fetchall()
    except Exception:
        rows = []
    conn.close()

    if not rows:
        logger.info("No GitHub trending found in DB")
        return

    docs = []
    for r in rows:
        d = dict(r)
        text = f"Repo: {d.get('repo_name','')} | {d.get('description','')} | Language: {d.get('language','')} | Stars: {d.get('stars','')} | Today Stars: {d.get('today_stars','')}"
        doc = Document(
            page_content=text,
            metadata={
                "source": "github_trending",
                "repo": d.get("repo_name", ""),
                "language": d.get("language", ""),
                "stars": d.get("stars", ""),
                "category": d.get("category", ""),
                "date": d.get("scrape_date", ""),
            }
        )
        docs.append(doc)

    _documents_to_chunks(docs, embedding_model, vector_db, COLL_GITHUB, dim, chunk_size=500)


def _load_policies(vector_db, embedding_model):
    """Load policy information into vector DB."""
    from deepsearcher import configuration as ds_config
    dim = embedding_model.dimension

    policies = [
        {"name": "等保 2.0", "description": "网络安全等级保护制度 2.0，要求云服务商具备等保三级及以上资质。关键基础设施需通过等保四级。华为云已通过等保四级认证。"},
        {"name": "信创替代", "description": "信息技术应用创新产业推进，要求政府和国企在 2027 年前完成核心系统国产化替代。涉及 CPU、操作系统、数据库、中间件等全栈国产化。"},
        {"name": "数据出境", "description": "《数据出境安全评估办法》要求向境外提供重要数据的企业通过安全评估。对跨国企业的数据本地化存储提出明确要求。"},
        {"name": "数字化补贴", "description": "各地方政府出台中小企业数字化改造补贴政策，单企业补贴金额 10-100 万不等。重点支持上云用数赋智。"},
        {"name": "SOC 报告", "description": "云服务商需提供 SOC 1/2/3 审计报告，作为企业采购云服务的合规依据。SOC 2 Type II 成为企业上云标配要求。"},
    ]

    docs = []
    for p in policies:
        text = f"{p['name']}: {p['description']}"
        doc = Document(
            page_content=text,
            metadata={
                "source": "policy",
                "name": p["name"],
            }
        )
        docs.append(doc)

    _documents_to_chunks(docs, embedding_model, vector_db, COLL_POLICY, dim, chunk_size=500)

# ──────────────────────────────────────────────
# Query API — used by main.py endpoints
# ──────────────────────────────────────────────

def deep_research(query_text: str, max_iter: int = 3) -> dict:
    """
    Perform deep research using DeepSearcher's iterative search + reasoning.

    This uses the RAGRouter which automatically selects between DeepSearch
    and ChainOfRAG agents based on the query type.

    Args:
        query_text: The research question or topic
        max_iter: Maximum iterations for deep search (higher = more thorough)

    Returns:
        dict with keys: answer (str), sources (list), tokens (int)
    """
    if not _is_initialized:
        init_deep_searcher()

    try:
        answer, sources, tokens = ds_query(query_text, max_iter=max_iter)
        return {
            "answer": answer,
            "sources": [{"text": s.text, "score": s.score, "metadata": s.metadata} for s in sources],
            "tokens": tokens,
        }
    except Exception as e:
        logger.error(f"Deep research failed: {e}")
        return {
            "answer": f"研究过程中出现错误: {str(e)}",
            "sources": [],
            "tokens": 0,
        }


def retrieve_context(query_text: str, top_k: int = 10) -> List[dict]:
    """
    Retrieve relevant context from vector DB for a query.
    Searches across all collections and returns ranked results.

    Args:
        query_text: The search query
        top_k: Number of results to return

    Returns:
        List of dicts with text, score, metadata, collection
    """
    if not _is_initialized:
        init_deep_searcher()

    from deepsearcher import configuration as ds_config
    embedding_model = ds_config.embedding_model
    vector_db = ds_config.vector_db

    # Workaround: embed_query with single string returns scalar in sentence-transformers
    # Always pass as list to get a proper 2D result
    query_vec = embedding_model._embed_input([query_text])[0]

    all_results = []
    for collection in ALL_COLLECTIONS:
        try:
            results = vector_db.search_data(collection=collection, vector=query_vec, top_k=max(3, top_k // len(ALL_COLLECTIONS)))
            for r in results:
                all_results.append({
                    "text": r.text,
                    "score": r.score,
                    "metadata": r.metadata,
                    "collection": collection,
                })
        except Exception as e:
            logger.debug(f"Search failed for collection '{collection}': {e}")

    # Sort by score descending
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:top_k]


def context_to_str(results: List[dict], max_chars: int = 6000) -> str:
    """
    Format retrieved context into a prompt string.
    Groups by collection and formats with sources.
    """
    if not results:
        return ""

    sections = []
    collection_groups = {}
    for r in results:
        coll = r.get("collection", "unknown")
        if coll not in collection_groups:
            collection_groups[coll] = []
        collection_groups[coll].append(r)

    for coll, items in collection_groups.items():
        label = coll.replace("_", " ").title()
        section = f"--- {label} ---\n"
        for i, item in enumerate(items, 1):
            section += f"[{i}] {item['text']}\n"
        sections.append(section)

    full = "\n".join(sections)
    if len(full) > max_chars:
        full = full[:max_chars] + "...\n[内容已截断]"
    return full


def chat_with_context(user_message: str, history: List[dict] = None) -> Tuple[str, List[dict]]:
    """
    Chat with RAG: retrieve context from vector DB, then generate answer.

    This is the non-streaming version. For streaming, see
    `stream_chat_with_context()` in main.py integration.

    Args:
        user_message: The user's question
        history: Previous chat history (list of {"role": ..., "content": ...})

    Returns:
        Tuple of (reply_text, retrieved_context_list)
    """
    if not _is_initialized:
        init_deep_searcher()

    # Step 1: Retrieve relevant context
    context_results = retrieve_context(user_message, top_k=10)
    context_str = context_to_str(context_results)

    # Step 2: Build prompt with context
    system_prompt = """你是 InsightPro 商业洞察平台的 AI 助手。请基于以下检索到的内部知识回答用户问题。

## 回答要求
1. 优先使用检索到的内部知识回答问题
2. 如果检索到的知识不足以回答，诚实告知用户并基于你的知识补充
3. 引用知识来源（如行业、数据类型）
4. 回答专业简洁，适合商业决策者阅读
5. 使用中文回答"""

    if context_str:
        system_prompt += f"\n\n## 检索到的内部知识\n{context_str}"

    # Step 3: Call DeepSeek API
    import httpx

    chat_api_url = os.getenv("CHAT_API_URL", "https://api.modelarts-maas.com/v2/chat/completions")
    chat_api_key = os.getenv("CHAT_API_KEY", "")
    chat_model = os.getenv("CHAT_MODEL", "deepseek-v3.2")

    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history[-6:])
    messages.append({"role": "user", "content": user_message})

    try:
        import httpx
        resp = httpx.post(
            chat_api_url,
            headers={"Authorization": f"Bearer {chat_api_key}"},
            json={
                "model": chat_model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 2048,
            },
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        reply = data["choices"][0]["message"]["content"]
        return reply, context_results
    except Exception as e:
        error_msg = f"AI 服务异常: {str(e)}"
        return error_msg, context_results
