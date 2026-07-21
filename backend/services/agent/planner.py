from services.ai_service import chat_complete, extract_json

PLANNER_PROMPT = """你是一位资深商业分析师。用户的商业分析问题是：

{query}

请分析这个问题，输出结构化的分析规划 JSON：

{{
  "analysis_type": "行业分析 / 竞品分析 / 商机识别 / 综合",
  "title": "分析报告标题",
  "research_steps": [
    {{
      "step_id": "step_1",
      "dimension": "分析维度",
      "data_needed": "需要什么数据",
      "data_source": "数据来源类型（行业新闻/招标/政策/友商动态/需求信号）",
      "key_question": "这个维度要回答的核心问题",
      "reason": "为什么需要这个分析"
    }}
  ],
  "expected_outline": ["章节1", "章节2", "章节3"],
  "complexity": "简单/中等/深度",
  "estimated_steps": 3
}}

要求：
1. 分析维度 3-6 个
2. data_source 必须是平台已有的数据源
3. 每个 step 的 key_question 要具体可回答
"""


class Planner:
    async def plan(self, query: str) -> dict:
        prompt = PLANNER_PROMPT.format(query=query)
        result = chat_complete(system_prompt="你输出结构化 JSON 规划。", user_prompt=prompt, temperature=0.3, max_tokens=2000)
        plan = extract_json(result)
        if not plan or "research_steps" not in plan:
            plan = {
                "analysis_type": "综合",
                "title": f"{query[:30]}...",
                "research_steps": [
                    {"step_id": "step_1", "dimension": "行业概况", "data_needed": "行业新闻和趋势", "data_source": "行业新闻", "key_question": f"{query}的行业概况", "reason": "了解行业基本面和最新动态"},
                    {"step_id": "step_2", "dimension": "政策环境", "data_needed": "相关政策法规", "data_source": "政策法规", "key_question": f"{query}的政策影响", "reason": "政策是行业变化的关键驱动因素"},
                    {"step_id": "step_3", "dimension": "市场机会", "data_needed": "招标和需求信号", "data_source": "招标信息", "key_question": f"{query}的市场机会", "reason": "识别具体的商业机会"},
                ],
                "expected_outline": ["行业概况", "政策环境", "市场机会", "建议"],
                "complexity": "中等",
                "estimated_steps": 3,
            }
        return plan
