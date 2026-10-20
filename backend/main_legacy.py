"""
Backward-compatibility re-exports from decomposed modules.

All functions have been moved to their proper homes:
  - crawlers/github_crawler.py   — GitHub scraping
  - crawlers/baidu_crawler.py    — Baidu hot search
  - services/evaluation_service.py — Business evaluation + project summaries
  - services/competitor_news_service.py — Competitor news
  - services/maintenance_service.py    — Data cleanup
  - services/research_service.py       — Deep research

Import from the new modules directly in new code.
"""
from crawlers.github_crawler import scrape_github_trending, refresh_and_store, _fetch_github_readme
from crawlers.baidu_crawler import _fetch_baidu_hotsearch_sync
from services.evaluation_service import (
    evaluate_trending_business,
    _parse_eval_json,
    BUSINESS_EVAL_SYSTEM_PROMPT,
)
from services.competitor_news_service import (
    get_competitor_news,
    get_competitor_summary,
    refresh_competitor_news,
)
from services.maintenance_service import cleanup_old_data
from services.research_service import deep_research
