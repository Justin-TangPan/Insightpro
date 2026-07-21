"""友商洞察路由"""
import asyncio
from fastapi import APIRouter, Depends, HTTPException
from routers.auth import require_auth
from datetime import datetime
from db import get_db
from crawlers import get_cloud_vendor_news
from main_legacy import refresh_competitor_news, get_competitor_summary

router = APIRouter()


@router.get("/competitors")
async def get_competitors():
    """获取友商洞察数据（行业知识 + DB 动态数据）"""
    from crawlers import get_cloud_vendor_news
    vendors_cfg = [
        {"name": "AWS", "region": "全球", "marketShare": "全球 32% · 中国区 < 5%",
         "products": ["Amazon Bedrock", "Amazon SageMaker", "Amazon Q", "AWS Lambda"],
         "strengths": ["全球基础设施最广", "AI/ML 服务成熟度最高", "企业生态完善"],
         "weaknesses": ["中国区功能滞后", "本地化支持不足", "价格体系复杂"],
         "vs_huawei": "AWS 全球化布局领先，但华为云在中国政企市场的本地化深度、端边云协同、一云多芯架构适配方面具有显著优势。"},
        {"name": "Microsoft Azure", "region": "全球", "marketShare": "全球 23% · 中国区 < 3%",
         "products": ["Azure AI Foundry", "Azure OpenAI Service", "Azure Arc"],
         "strengths": ["OpenAI 独占整合", "企业办公生态绑定", "混合云 Azure Arc"],
         "weaknesses": ["中国节点带宽受限", "AI 服务定价偏高", "开源社区信任度一般"],
         "vs_huawei": "Azure 的 Copilot + OpenAI 整合优势明显，但华为云在 AI 算力自主可控、国产化替代完整方案上具备差异化竞争力。"},
        {"name": "阿里云", "region": "中国", "marketShare": "国内 34% · 第一",
         "products": ["通义千问", "百炼平台", "PAI", "PolarDB"],
         "strengths": ["国内市场份额第一", "双11高并发验证", "钉钉企业入口"],
         "weaknesses": ["海外市场拓展受限", "政企客户深度不足", "AI 大模型商业化慢"],
         "vs_huawei": "阿里云在互联网行业和开发者生态上领先，但华为云在政府、金融、制造行业覆盖深度、端边云全栈能力上更具优势。"},
        {"name": "腾讯云", "region": "中国", "marketShare": "国内 16% · 第三",
         "products": ["混元大模型", "TI-ONE", "大模型知识引擎 LKE", "TDSQL"],
         "strengths": ["微信 13 亿用户生态", "游戏行业深度覆盖", "实时音视频领先"],
         "weaknesses": ["企业服务基因较弱", "AI 大模型布局较慢", "toB 服务体系不完善"],
         "vs_huawei": "腾讯云在文娱社交和实时音视频场景占据优势，但华为云在严肃企业级市场、工业互联网、AI 大模型行业落地方面具备更强的综合服务能力。"},
        {"name": "火山云", "region": "中国", "marketShare": "国内 5% · 增速最快",
         "products": ["豆包大模型", "火山方舟", "扣子 Coze"],
         "strengths": ["抖音电商生态", "AI 推理价格最低", "增长策略灵活"],
         "weaknesses": ["市场份额较小", "企业级能力验证不足", "行业覆盖窄"],
         "vs_huawei": "火山云依托字节生态在增长策略和 AI 算法上表现突出，但华为云在企业级产品系统性、行业覆盖广度上具有压倒性优势。"},
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
        except Exception:
            v["recent_news_count"] = 0
            v["score"] = 70
            v["recent_highlights"] = []

    return {"vendors": vendors_cfg, "source": "database", "date": datetime.now().strftime("%Y-%m-%d")}


@router.get("/competitors/summary")
async def competitors_summary():
    """获取每个云厂商的最新新闻摘要，按厂商分组"""
    from main_legacy import get_competitor_summary
    summary = get_competitor_summary(limit_per_vendor=3)
    summary.pop("华为云", None)
    if not summary:
        try:
            await asyncio.to_thread(refresh_competitor_news)
            summary = get_competitor_summary(limit_per_vendor=3)
        except Exception:
            pass
    total = sum(len(items) for items in summary.values())
    return {"vendors": summary, "total": total, "count": len(summary)}


@router.post("/competitors/refresh")
async def competitors_refresh(_=Depends(require_auth)):
    """手动触发友商动态刷新"""
    try:
        count = await asyncio.to_thread(refresh_competitor_news)
        return {"status": "ok", "count": count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"刷新失败: {e}")
