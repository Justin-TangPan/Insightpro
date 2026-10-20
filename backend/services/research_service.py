"""Deep research wrapper."""
import logging

logger = logging.getLogger(__name__)


async def deep_research(query: str, max_iter: int = 2) -> dict:
    try:
        from deep_searcher_integration import deep_research as dr
        return await dr(query, max_iter=max_iter)
    except Exception as e:
        logger.warning("deep research failed: %s", e)
        return {"answer": "Deep research is temporarily unavailable, please try again later", "sources": []}
