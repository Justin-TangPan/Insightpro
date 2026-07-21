from services.ai_service import chat_complete
import json

REPORTER_SYSTEM_PROMPT = """你是一位资深商业分析师。基于以下分析结果和验证报告，生成一份结构化的商业分析报告。

报告要求：
1. 执行摘要（300 字以内，供决策者快速阅读）
2. 分维度分析（每个维度含：核心发现、数据支撑、置信度）
3. 综合判断（市场前景、竞争态势、风险提示）
4. 行动建议（按优先级排序，每条建议含：具体行动、预期效果、时间窗口）
5. 不确定性说明（哪些结论需要进一步验证）
6. 数据来源汇总（列出所有引用的数据源）

格式：Markdown
风格：专业、客观、有据可查
"""


class Reporter:
    async def generate(self, query: str, plan: dict, analysis: dict, verification: dict) -> dict:
        context = {"原始问题": query, "分析规划": plan, "分析结果": analysis, "验证报告": verification}
        context_str = json.dumps(context, ensure_ascii=False, indent=2)
        result = chat_complete(
            system_prompt=REPORTER_SYSTEM_PROMPT,
            user_prompt=f"请根据以下分析数据生成报告：\n\n{context_str[:6000]}",
            temperature=0.5, max_tokens=4000,
        )
        return {
            "markdown": result,
            "metadata": {
                "query": query,
                "analysis_type": plan.get("analysis_type", "综合"),
                "confidence": verification.get("overall_confidence", 0.0),
                "dimensions_analyzed": analysis.get("total_dimensions", 0),
                "verified_claims": len(verification.get("verified_claims", [])),
                "unverified_claims": len(verification.get("unverified_claims", [])),
            },
        }
