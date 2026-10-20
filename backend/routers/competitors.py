"""Competitor insights routes"""
import asyncio, logging
from fastapi import APIRouter, Depends, HTTPException
from routers.auth import require_auth
from datetime import datetime
from db import get_db
from crawlers import get_cloud_vendor_news
from main_legacy import refresh_competitor_news, get_competitor_summary

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/competitors")
async def get_competitors():
    """Get competitor insights data (industry knowledge + DB dynamic data)"""
    from crawlers import get_cloud_vendor_news
    vendors_cfg = [
        {"name": "AWS", "region": "Global", "marketShare": "Global 32% · China < 5%",
         "products": ["Amazon Bedrock", "Amazon SageMaker", "Amazon Q", "AWS Lambda"],
         "strengths": ["Broadest global infrastructure", "Highest AI/ML service maturity", "Mature enterprise ecosystem"],
         "weaknesses": ["China region feature lag", "Insufficient localization support", "Complex pricing structure"],
         "vs_huawei": "AWS leads in global deployment, but Huawei Cloud has significant advantages in China's government and enterprise market localization depth, edge-cloud synergy, and one-cloud-multi-architecture adaptation."},
        {"name": "Microsoft Azure", "region": "Global", "marketShare": "Global 23% · China < 3%",
         "products": ["Azure AI Foundry", "Azure OpenAI Service", "Azure Arc"],
         "strengths": ["Exclusive OpenAI integration", "Enterprise office ecosystem lock-in", "Hybrid cloud Azure Arc"],
         "weaknesses": ["China node bandwidth limited", "AI service pricing high", "Moderate open-source community trust"],
         "vs_huawei": "Azure's Copilot + OpenAI integration advantage is clear, but Huawei Cloud has differentiated competitiveness in AI compute autonomy and complete domestic substitution solutions."},
        {"name": "Alibaba Cloud", "region": "China", "marketShare": "China 34% · #1",
         "products": ["Tongyi Qianwen", "Bailian Platform", "PAI", "PolarDB"],
         "strengths": ["#1 domestic market share", "Double 11 high-concurrency validation", "DingTalk enterprise entry"],
         "weaknesses": ["Overseas expansion limited", "Insufficient government/enterprise depth", "Slow AI large model commercialization"],
         "vs_huawei": "Alibaba Cloud leads in internet industry and developer ecosystem, but Huawei Cloud has advantages in government, finance, and manufacturing industry coverage depth and full-stack edge-cloud capabilities."},
        {"name": "Tencent Cloud", "region": "China", "marketShare": "China 16% · #3",
         "products": ["Hunyuan Large Model", "TI-ONE", "LKE Knowledge Engine", "TDSQL"],
         "strengths": ["WeChat 1.3B user ecosystem", "Deep gaming industry coverage", "Leading real-time audio/video"],
         "weaknesses": ["Weak enterprise service DNA", "Slow AI large model rollout", "Incomplete B2B service system"],
         "vs_huawei": "Tencent Cloud excels in entertainment/social and real-time audio/video scenarios, but Huawei Cloud has stronger comprehensive service capabilities in serious enterprise markets, industrial IoT, and AI large model industry deployment."},
        {"name": "Volcengine", "region": "China", "marketShare": "Significant China market participant",
         "products": ["Doubao Large Model", "Volcengine Ark", "Coze"],
         "strengths": ["Douyin e-commerce ecosystem", "Lowest AI inference pricing", "Flexible growth strategies"],
         "weaknesses": ["Smaller market share", "Insufficient enterprise-grade validation", "Narrow industry coverage"],
         "vs_huawei": "Volcengine stands out in growth strategies and AI algorithms leveraging ByteDance ecosystem, but Huawei Cloud has overwhelming advantages in enterprise-grade product systematicity and industry coverage breadth."},
    ]

    for v in vendors_cfg:
        try:
            news = get_cloud_vendor_news(days=7, vendor=v["name"], limit=10)
            v["recent_news_count"] = len(news)
            v["score"] = min(95, 60 + len(news) * 5)
            if news:
                v["recent_highlights"] = [n["title"] for n in news[:3] if n.get("title")]
            else:
                v["recent_highlights"] = []
        except Exception as e:
            logger.warning("vendor news fallback for %s: %s", v["name"], e)
            v["recent_news_count"] = 0
            v["score"] = 70
            v["recent_highlights"] = []

    return {"vendors": vendors_cfg, "source": "database", "date": datetime.now().strftime("%Y-%m-%d")}


@router.get("/competitors/summary")
async def competitors_summary():
    """Get the latest news summary for each cloud vendor, grouped by vendor"""
    from main_legacy import get_competitor_summary
    summary = get_competitor_summary(limit_per_vendor=8)
    summary.pop("Huawei Cloud", None)
    if not summary:
        try:
            await asyncio.to_thread(refresh_competitor_news)
            summary = get_competitor_summary(limit_per_vendor=8)
        except Exception as e:
            logger.warning("competitor summary refresh fallback: %s", e)
    total = sum(len(items) for items in summary.values())
    return {"vendors": summary, "total": total, "count": len(summary)}


@router.post("/competitors/refresh")
async def competitors_refresh(_=Depends(require_auth)):
    """Manually trigger competitor news refresh"""
    try:
        from services.task_service import run_task
        count = await asyncio.to_thread(run_task, "competitor_daily", "manual", refresh_competitor_news)
        return {"status": "ok", "count": count}
    except Exception as e:
        logger.exception("competitor refresh failed")
        raise HTTPException(status_code=500, detail="Refresh failed, please try again later")
